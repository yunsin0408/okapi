from __future__ import annotations

from typing import Dict, Any, Optional, List
from services.mongo_service import find_many, find_one, update_one


class QuizStoryTool:
    """
    閱讀人格測驗工具。

    功能：
    1. start_quiz：開始測驗，從 quiz_questions 取第一題
    2. answer_quiz：接收使用者選項，累積分數
    3. get_result：根據最高分角色回傳結果
    """

    DEFAULT_QUIZ_ID = "reading_personality_quiz"

    def start_quiz(self, user_id: str) -> Dict[str, Any]:
        questions = self._get_questions()

        if not questions:
            return {
                "type": "quiz_story",
                "text": "目前資料庫沒有測驗題目，請先建立 quiz_questions 資料。",
                "error_code": "NO_QUIZ_QUESTIONS",
                "options": [],
            }

        first_question = questions[0]

        self._save_quiz_state(
            user_id=user_id,
            state={
                "user_id": user_id,
                "quiz_id": self.DEFAULT_QUIZ_ID,
                "current_question_index": 0,
                "scores": {},
                "answers": [],
                "status": "in_progress",
            },
        )

        return self._format_question_response(first_question, index=0, total=len(questions))

    def answer_quiz(
        self,
        user_id: str,
        interaction_id: Optional[str] = None,
        user_input: Optional[str] = None,
    ) -> Dict[str, Any]:
        state = self._get_quiz_state(user_id)

        if not state:
            return {
                "type": "quiz_story",
                "text": "目前沒有進行中的測驗，請重新開始測驗。",
                "error_code": "NO_ACTIVE_QUIZ",
                "action_type": "CHAT",
            }

        questions = self._get_questions()

        if not questions:
            return {
                "type": "quiz_story",
                "text": "目前資料庫沒有測驗題目，請先建立 quiz_questions 資料。",
                "error_code": "NO_QUIZ_QUESTIONS",
                "action_type": "CHAT",
            }

        current_index = state.get("current_question_index", 0)

        if current_index >= len(questions):
            return self.get_result(user_id)

        current_question = questions[current_index]
        selected_option = self._find_selected_option(current_question, user_input)

        if not selected_option:
            return {
                "type": "quiz_story",
                "text": "我沒有找到這個選項，請選擇題目中的 A、B、C 或 D。",
                "error_code": "INVALID_QUIZ_OPTION",
                "question": current_question.get("question_text"),
                "options": self._format_options(current_question),
                "action_type": "SHOW_QUIZ",
            }

        scores = state.get("scores", {})
        option_scores = selected_option.get("character_scores", {})

        for character_key, score in option_scores.items():
            scores[character_key] = scores.get(character_key, 0) + score

        answers = state.get("answers", [])
        answers.append({
            "question_id": current_question.get("_id"),
            "option_id": selected_option.get("option_id"),
            "option_text": selected_option.get("text"),
        })

        next_index = current_index + 1

        self._save_quiz_state(
            user_id=user_id,
            state={
                **state,
                "current_question_index": next_index,
                "scores": scores,
                "answers": answers,
            },
        )

        if next_index >= len(questions):
            return self.get_result(user_id)

        next_question = questions[next_index]
        return self._format_question_response(
            next_question,
            index=next_index,
            total=len(questions),
        )

    def get_result(self, user_id: str) -> Dict[str, Any]:
        state = self._get_quiz_state(user_id)

        if not state:
            return {
                "type": "quiz_result",
                "text": "目前沒有測驗結果，請先完成測驗。",
                "error_code": "NO_QUIZ_RESULT",
                "action_type": "CHAT",
            }

        scores = state.get("scores", {})

        if not scores:
            return {
                "type": "quiz_result",
                "text": "目前沒有足夠的測驗分數，請重新測驗一次。",
                "error_code": "EMPTY_QUIZ_SCORE",
                "action_type": "CHAT",
            }

        top_character_key = max(scores, key=scores.get)

        result_doc = find_one(
            "quiz_results",
            {
                "character_key": top_character_key,
            },
        )

        if not result_doc:
            result_doc = find_one(
                "characters",
                {
                    "character_key": top_character_key,
                },
            )

        self._save_quiz_state(
            user_id=user_id,
            state={
                **state,
                "status": "completed",
                "result_character_key": top_character_key,
            },
        )

        if not result_doc:
            return {
                "type": "quiz_result",
                "text": f"你的閱讀人格結果是：{top_character_key}。但目前資料庫還沒有這個角色的完整介紹。",
                "character_key": top_character_key,
                "scores": scores,
                "action_type": "SHOW_QUIZ_RESULT",
            }

        character_name = (
            result_doc.get("character_name")
            or result_doc.get("name")
            or top_character_key
        )

        analysis = (
            result_doc.get("analysis")
            or result_doc.get("description")
            or "這個結果代表你目前適合從貼近自己狀態的內容開始閱讀。"
        )

        quote = result_doc.get("quote")

        text = f"你的閱讀人格是：{character_name}。\n{analysis}"

        if quote:
            text += f"\n\n送你一句話：{quote}"

        return {
            "type": "quiz_result",
            "text": text,
            "character_key": top_character_key,
            "character_name": character_name,
            "analysis": analysis,
            "quote": quote,
            "scores": scores,
            "result": result_doc,
            "action_type": "SHOW_QUIZ_RESULT",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_questions(self) -> List[Dict[str, Any]]:
        questions = find_many(
            "quiz_questions",
            {
                "quiz_id": self.DEFAULT_QUIZ_ID,
            },
            limit=50,
        )

        if not questions:
            questions = find_many(
                "quiz_questions",
                {},
                limit=50,
            )

        return sorted(questions, key=lambda q: q.get("order", 999))

    def _get_quiz_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        return find_one(
            "quiz_states",
            {
                "user_id": user_id,
                "quiz_id": self.DEFAULT_QUIZ_ID,
            },
        )

    def _save_quiz_state(self, user_id: str, state: Dict[str, Any]) -> None:
        update_one(
            "quiz_states",
            {
                "user_id": user_id,
                "quiz_id": self.DEFAULT_QUIZ_ID,
            },
            state,
        )

    def _format_question_response(
        self,
        question: Dict[str, Any],
        index: int,
        total: int,
    ) -> Dict[str, Any]:
        return {
            "type": "quiz_story",
            "text": f"第 {index + 1} 題 / 共 {total} 題：{question.get('question_text')}",
            "interaction_id": self.DEFAULT_QUIZ_ID,
            "question_id": question.get("_id"),
            "question": question.get("question_text"),
            "progress": {
                "current": index + 1,
                "total": total,
            },
            "options": self._format_options(question),
            "action_type": "SHOW_QUIZ",
        }

    def _format_options(self, question: Dict[str, Any]) -> List[Dict[str, str]]:
        options = question.get("options", [])

        formatted = []

        for option in options:
            formatted.append({
                "id": option.get("option_id"),
                "text": option.get("text"),
            })

        return formatted

    def _find_selected_option(
        self,
        question: Dict[str, Any],
        user_input: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not user_input:
            return None

        cleaned = user_input.strip().upper()
        options = question.get("options", [])

        for option in options:
            option_id = str(option.get("option_id", "")).upper()
            option_text = str(option.get("text", ""))

            if cleaned == option_id:
                return option

            if cleaned in option_text:
                return option

        return None


quiz_story_tool = QuizStoryTool()