"""Context window management for AI agents with limited context."""
import tiktoken
import json
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class TruncationResult:
    data: Any
    truncated: bool
    original_count: int
    returned_count: int
    estimated_tokens: int

class ContextWindowManager:
    def __init__(self, max_tokens: int = 40000):
        self.max_tokens = max_tokens
        self.encoder = tiktoken.get_encoding("cl100k_base")
        
    def estimate_tokens(self, data: Any) -> int:
        """Estimate tokens for any JSON-serializable data"""
        text = json.dumps(data, default=str)
        return len(self.encoder.encode(text))
    
    def truncate_list_response(
        self, 
        items: List[Dict], 
        max_items: int,
        preview_fields: List[str] = None
    ) -> TruncationResult:
        """Truncate list responses intelligently"""
        original_count = len(items)
        
        # Start with max items
        truncated_items = items[:max_items]
        
        # If preview fields specified, create preview versions
        if preview_fields:
            preview_items = []
            for item in truncated_items:
                preview_item = {k: v for k, v in item.items() if k in preview_fields}
                preview_items.append(preview_item)
            truncated_items = preview_items
        
        # Check token count and further truncate if needed
        current_tokens = self.estimate_tokens(truncated_items)
        
        while current_tokens > self.max_tokens and len(truncated_items) > 1:
            truncated_items = truncated_items[:-1]
            current_tokens = self.estimate_tokens(truncated_items)
        
        return TruncationResult(
            data=truncated_items,
            truncated=len(truncated_items) < original_count,
            original_count=original_count,
            returned_count=len(truncated_items),
            estimated_tokens=current_tokens
        )
    
    def create_truncated_response(self, result: TruncationResult, entity_type: str) -> Dict:
        """Create standardized truncated response with AI instructions"""
        response = {
            'data': result.data,
            'meta': {
                'total_items': result.original_count,
                'returned_items': result.returned_count,
                'truncated': result.truncated,
                'estimated_tokens': result.estimated_tokens
            }
        }
        
        if result.truncated:
            suggestions = self._get_refinement_suggestions(entity_type)
            response['assistant_instruction'] = (
                f"⚠️ Response truncated for context window optimization.\n"
                f"Found {result.original_count} {entity_type} but returned only {result.returned_count}.\n"
                f"To get better results, please:\n" + 
                "\n".join(f"• {s}" for s in suggestions)
            )
        
        return response
    
    def _get_refinement_suggestions(self, entity_type: str) -> List[str]:
        """Get entity-specific refinement suggestions"""
        base_suggestions = [
            "Use more specific search terms",
            "Add a timeframe (e.g., 'last 7 days', 'this month')",
            "Search by specific ID if known"
        ]
        
        if entity_type == "conversations":
            base_suggestions.extend([
                "Filter by customer email",
                "Filter by conversation state (open, closed, snoozed)"
            ])
        elif entity_type == "articles":
            base_suggestions.extend([
                "Search by article title keywords",
                "Use get_article with a specific ID for full content"
            ])
        elif entity_type == "tickets":
            base_suggestions.extend([
                "Filter by ticket state",
                "Filter by ticket type",
                "Search by customer email"
            ])
        
        return base_suggestions

# Global instance
context_manager = ContextWindowManager()