"""Ticket tools for Fast Intercom MCP."""
from typing import Optional, Dict, List
from ..server import mcp
from ..api.client import IntercomAPIClient
from ..utils.context_window import context_manager
from ..config import Config
import logging

logger = logging.getLogger(__name__)

api_client = IntercomAPIClient(Config.load().intercom_token)

@mcp.tool()
async def search_tickets(
    query: Optional[str] = None,
    customer_email: Optional[str] = None,
    ticket_state: Optional[str] = None,
    ticket_type_id: Optional[str] = None,
    limit: int = 20
) -> Dict:
    """
    Search tickets without local storage. Queries Intercom API directly.
    
    Args:
        query: Text to search in ticket content
        customer_email: Filter by customer email
        ticket_state: Filter by state (submitted, in_progress, waiting_on_customer, on_hold, resolved)
        ticket_type_id: Filter by ticket type ID
        limit: Maximum tickets to return
    """
    try:
        # Build search query for Intercom API
        search_query = {
            "query": {}
        }
        
        # Add filters based on parameters
        filters = []
        
        if customer_email:
            filters.append({
                "field": "contact.email",
                "operator": "=",
                "value": customer_email
            })
        
        if ticket_state:
            filters.append({
                "field": "state",
                "operator": "=",
                "value": ticket_state
            })
        
        if ticket_type_id:
            filters.append({
                "field": "ticket_type_id",
                "operator": "=",
                "value": ticket_type_id
            })
        
        if filters:
            search_query["query"]["filter"] = {
                "type": "AND",
                "filters": filters
            }
        
        # Execute search
        response = await api_client.search_tickets(search_query)
        
        tickets = response.get('data', [])
        total_count = response.get('total_count', 0)
        
        # Process tickets for response
        processed_tickets = []
        for ticket in tickets:
            processed = {
                'id': ticket['id'],
                'ticket_id': ticket.get('ticket_id'),
                'category': ticket.get('category'),
                'ticket_state': ticket.get('ticket_state', {}).get('name'),
                'ticket_type': ticket.get('ticket_type', {}).get('name'),
                'created_at': ticket.get('created_at'),
                'updated_at': ticket.get('updated_at'),
                'is_open': ticket.get('open'),
                'assigned_to': None,
                'contacts': []
            }
            
            # Extract assignee info
            if 'admin_assignee_id' in ticket and ticket['admin_assignee_id']:
                processed['assigned_to'] = {
                    'type': 'admin',
                    'id': ticket['admin_assignee_id']
                }
            elif 'team_assignee_id' in ticket and ticket['team_assignee_id']:
                processed['assigned_to'] = {
                    'type': 'team',
                    'id': ticket['team_assignee_id']
                }
            
            # Extract contact info
            for contact in ticket.get('contacts', {}).get('contacts', []):
                processed['contacts'].append({
                    'id': contact.get('id'),
                    'email': contact.get('email')
                })
            
            # Add ticket attributes preview
            if 'ticket_attributes' in ticket:
                attrs = ticket['ticket_attributes']
                processed['title'] = attrs.get('_default_title_', 'No title')
                processed['description_preview'] = (attrs.get('_default_description_', '')[:200] + '...' 
                                                   if len(attrs.get('_default_description_', '')) > 200 
                                                   else attrs.get('_default_description_', ''))
            
            processed_tickets.append(processed)
        
        # Apply truncation
        truncation_result = context_manager.truncate_list_response(
            processed_tickets,
            max_items=limit,
            preview_fields=['id', 'ticket_id', 'title', 'ticket_state', 'created_at', 'contacts']
        )
        
        response = context_manager.create_truncated_response(truncation_result, "tickets")
        response['meta']['total_found'] = total_count
        
        if query:
            response['meta']['search_query'] = query
        
        return response
        
    except Exception as e:
        logger.error(f"Error searching tickets: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': 'Error searching tickets. Please try different search criteria.'
        }

@mcp.tool()
async def get_ticket(ticket_id: str, include_parts: bool = True) -> Dict:
    """
    Get detailed information about a specific ticket.
    
    Args:
        ticket_id: The Intercom ticket ID
        include_parts: Whether to include ticket parts (comments/notes)
    """
    try:
        ticket = await api_client.get_ticket(ticket_id)
        
        # Process ticket parts if included
        if include_parts and 'ticket_parts' in ticket:
            parts = ticket['ticket_parts'].get('ticket_parts', [])
            config = Config.load()
            
            # Limit parts for context window
            if len(parts) > config.max_conversation_messages:
                ticket['ticket_parts']['ticket_parts'] = parts[:config.max_conversation_messages]
                ticket['_truncated_parts'] = True
                ticket['_total_parts'] = len(parts)
        
        return ticket
        
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': f'Could not retrieve ticket {ticket_id}. Please verify the ID.'
        }

@mcp.tool()
async def list_ticket_types() -> Dict:
    """
    List all available ticket types.
    """
    try:
        response = await api_client.list_ticket_types()
        
        ticket_types = response.get('data', [])
        
        # Simplify response
        processed_types = []
        for tt in ticket_types:
            processed = {
                'id': tt['id'],
                'name': tt['name'],
                'description': tt.get('description', ''),
                'icon': tt.get('icon', ''),
                'category': tt.get('category'),
                'is_internal': tt.get('is_internal', False),
                'archived': tt.get('archived', False)
            }
            processed_types.append(processed)
        
        return {
            'ticket_types': processed_types,
            'total': len(processed_types)
        }
        
    except Exception as e:
        logger.error(f"Error listing ticket types: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': 'Error listing ticket types. Please try again.'
        }

@mcp.tool()
async def list_ticket_states() -> Dict:
    """
    List all available ticket states.
    """
    try:
        response = await api_client.list_ticket_states()
        
        states = response.get('data', [])
        
        # Simplify response
        processed_states = []
        for state in states:
            processed = {
                'id': state['id'],
                'name': state['name'],
                'state': state.get('state'),
                'description': state.get('description', ''),
                'archived': state.get('archived', False)
            }
            processed_states.append(processed)
        
        return {
            'ticket_states': processed_states,
            'total': len(processed_states)
        }
        
    except Exception as e:
        logger.error(f"Error listing ticket states: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': 'Error listing ticket states. Please try again.'
        }