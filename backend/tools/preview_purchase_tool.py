from typing import Dict, Any, Optional
from services.book_service import book_service


class PreviewPurchaseTool:
    def run(
        self,
        user_id: str,
        current_book_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not current_book_id:
            return {
                "type": "preview_purchase",
                "text": "我目前還不知道你想看哪一本書的試讀或購買連結。可以先選一本推薦書。",
                "error_code": "MISSING_CURRENT_BOOK_ID",
                "actions": [],
            }

        book = book_service.get_book_by_id(current_book_id)

        if not book:
            return {
                "type": "preview_purchase",
                "text": "目前查不到這本書的資料，請確認 current_book_id 是否正確。",
                "book_id": current_book_id,
                "error_code": "BOOK_NOT_FOUND",
                "actions": [],
            }

        actions = []

        if book.sample_link:
            actions.append({
                "label": "查看試讀",
                "action": "preview",
                "url": book.sample_link,
            })

        if book.purchase_url:
            actions.append({
                "label": "前往購買",
                "action": "purchase",
                "url": book.purchase_url,
            })

        return {
            "type": "preview_purchase",
            "text": f"這裡是《{book.title}》的試讀與購買資訊。",
            "book_id": book.id,
            "book_title": book.title,
            "purchase_url": book.purchase_url,
            "sample_link": book.sample_link,
            "actions": actions,
        }


preview_purchase_tool = PreviewPurchaseTool()