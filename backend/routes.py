from fastapi import APIRouter, HTTPException, WebSocket
from schemas import (agentCreation, walletAddress, ChatAuthorization, 
                    agentInteract, agentInteractResponse)
from Agent import CreateAgent, load_agent, get_wallet_id
from chat_websockets import ChatWebSocket
from typing import Dict
import os
import json

# Create a router instead of an app
router = APIRouter()

# Store chat authorizations in memory
chat_authorizations: Dict[str, ChatAuthorization] = {}

# File path for authorizations
AUTHORIZATIONS_FILE = 'authorisations.json'

# Initialize WebSocket handler
chat_websocket = ChatWebSocket(chat_authorizations)

@router.post("/create-agent/{user_id}", response_model=walletAddress)
async def create_agent(user_id: str, request: agentCreation) -> walletAddress:
    try:
        # here teh walle address is being returned
        response = CreateAgent(prompt=request.prompt, NFT_id=request.nftHash)
        
        # Add debug logging
        print(f"Creating agent for user: {user_id}")
        print(f"NFT hash: {request.nftHash}")
        
        chat_auth = ChatAuthorization(
            creator=user_id.lower(),  # Store lowercase
            members=[]
        )
        
        chat_authorizations[request.nftHash] = chat_auth
        print(f"Updated chat authorizations: {chat_authorizations}")
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent-interact/{nft_hash}/{user_id}", response_model=agentInteractResponse)
async def interact_with_agent(
    nft_hash: str, 
    user_id: str, 
    request: agentInteract
) -> agentInteractResponse:
    if nft_hash not in chat_authorizations:
        raise HTTPException(
            status_code=404,
            detail="NFT hash not found in authorization map"
        )
    
    auth = chat_authorizations[nft_hash]
    
    if user_id != auth.creator and user_id not in auth.members:
        raise HTTPException(
            status_code=403,
            detail="User not authorized to interact with this agent"
        )
    
    try:
        response = load_agent(NFT_id=nft_hash, prompt=request.prompt)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{nft_hash}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, nft_hash: str, user_id: str):
    # Add debug logging
    print(f"WebSocket connection attempt:")
    print(f"NFT hash: {nft_hash}")
    print(f"User ID: {user_id}")
    print(f"Current authorizations: {chat_authorizations}")
    
    await chat_websocket.handle_websocket_connection(websocket, nft_hash, user_id)

@router.post("/add-chat-member/{nft_hash}/{new_member}")
async def add_chat_member(nft_hash: str, new_member: str, creator_id: str):
    if nft_hash not in chat_authorizations:
        raise HTTPException(
            status_code=404,
            detail="NFT hash not found"
        )
    
    auth = chat_authorizations[nft_hash]
    if creator_id != auth.creator:
        raise HTTPException(
            status_code=403,
            detail="Only the creator can add members"
        )
    
    if new_member not in auth.members:
        auth.members.append(new_member)
        return {"status": "success", "message": f"Added {new_member} to chat"}
    
    return {"status": "info", "message": "Member already exists in chat"}

@router.get("/fetch-agent-mappings")
async def fetch_agent_mappings():
    """Fetch all mappings between NFT hashes, wallet IDs, and conversation prompts."""
    try:
        # Get NFT to wallet mappings
        nft_wallet_map = {}
        if os.path.exists('map.json'):
            try:
                with open('map.json', 'r') as file:
                    nft_wallet_map = json.load(file)
            except json.JSONDecodeError:
                nft_wallet_map = {}
        
        # Get wallet conversations
        wallet_conversations = {}
        if os.path.exists('conversations.json'):
            try:
                with open('conversations.json', 'r') as file:
                    wallet_conversations = json.load(file)
            except json.JSONDecodeError:
                wallet_conversations = {}
        
        # Get agent personalities (if needed)
        agent_personalities = {}
        db_dir = "DB"
        if os.path.exists(db_dir):
            for filename in os.listdir(db_dir):
                if filename.endswith('.json'):
                    wallet_address = filename[:-5]  # Remove .json extension
                    file_path = os.path.join(db_dir, filename)
                    try:
                        with open(file_path, 'r') as file:
                            data = json.load(file)
                            agent_personalities[wallet_address] = {
                                "personality": data.get("Personality", ""),
                                "concepts": data.get("Concepts", [])
                            }
                    except:
                        continue
        
        # Combine data into a comprehensive mapping
        result = []
        for nft_hash, wallet_id in nft_wallet_map.items():
            entry = {
                "nft_hash": nft_hash,
                "wallet_id": wallet_id,
                "address": "",  # Would need to fetch this from wallet data
                "conversation": wallet_conversations.get(wallet_id, "No conversations yet")
            }
            
            # Get wallet data if available
            wallet_file = f"wallet_storage/{wallet_id}.json"
            if os.path.exists(wallet_file):
                try:
                    with open(wallet_file, 'r') as file:
                        wallet_data = json.load(file)
                        if wallet_data.get('addresses') and len(wallet_data['addresses']) > 0:
                            entry["address"] = wallet_data['addresses'][0].get('address_id', "")
                except:
                    pass
            
            # Add personality if available
            if entry["address"] in agent_personalities:
                entry["personality"] = agent_personalities[entry["address"]]
            
            result.append(entry)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-get-wallet/{nft_hash}")
async def test_get_wallet(nft_hash: str):
    """Test route to get wallet ID for an NFT hash."""
    return {"nft_hash": nft_hash, "wallet_id": get_wallet_id(nft_hash)}

@router.get("/user-agents/{user_id}")
async def get_user_agents(user_id: str):
    """
    Fetch all agents and their conversations that a user has access to.
    This includes both agents created by the user and those they're added to as members.
    """
    try:
        user_id = user_id.lower()  # Normalize user ID
        user_agents = []
        
        # Find all NFTs this user has access to
        accessible_nfts = []
        for nft_hash, auth in chat_authorizations.items():
            if auth.creator == user_id or user_id in auth.members:
                accessible_nfts.append({
                    "nft_hash": nft_hash,
                    "is_creator": auth.creator == user_id,
                    "members": auth.members
                })
        
        # Get NFT to wallet mappings
        nft_wallet_map = {}
        if os.path.exists('map.json'):
            try:
                with open('map.json', 'r') as file:
                    nft_wallet_map = json.load(file)
            except json.JSONDecodeError:
                nft_wallet_map = {}
        
        # Get wallet conversations
        wallet_conversations = {}
        if os.path.exists('conversations.json'):
            try:
                with open('conversations.json', 'r') as file:
                    wallet_conversations = json.load(file)
            except json.JSONDecodeError:
                wallet_conversations = {}
        
        # Build detailed information for each accessible NFT
        for nft_info in accessible_nfts:
            nft_hash = nft_info["nft_hash"]
            wallet_id = nft_wallet_map.get(nft_hash)
            
            if not wallet_id:
                continue  # Skip if no wallet mapping
                
            # Get agent details
            agent_entry = {
                "nft_hash": nft_hash,
                "wallet_id": wallet_id,
                "is_creator": nft_info["is_creator"],
                "members": nft_info["members"],
                "conversation": wallet_conversations.get(wallet_id, "No conversations yet"),
                "address": "",
                "personality": {}
            }
            
            # Get wallet address
            wallet_file = f"wallet_storage/{wallet_id}.json"
            if os.path.exists(wallet_file):
                try:
                    with open(wallet_file, 'r') as file:
                        wallet_data = json.load(file)
                        if wallet_data.get('addresses') and len(wallet_data['addresses']) > 0:
                            agent_entry["address"] = wallet_data['addresses'][0].get('address_id', "")
                except:
                    pass
            
            # Get agent personality
            if agent_entry["address"]:
                db_file = f"DB/{agent_entry['address']}.json"
                if os.path.exists(db_file):
                    try:
                        with open(db_file, 'r') as file:
                            data = json.load(file)
                            agent_entry["personality"] = {
                                "description": data.get("Personality", ""),
                                "concepts": data.get("Concepts", []),
                                "tools": data.get("Tools", [])
                            }
                    except:
                        pass
            
            # Parse conversations into an array for better frontend display
            if isinstance(agent_entry["conversation"], str):
                # Try to parse conversation string into structured data
                conversation_parts = []
                try:
                    # Typical format: "Question:X,answer: Y"
                    convo_str = agent_entry["conversation"]
                    if "Question:" in convo_str and ",answer: " in convo_str:
                        question_part = convo_str.split(",answer: ")[0]
                        answer_part = convo_str.split(",answer: ")[1]
                        
                        question = question_part.replace("Question:", "").strip()
                        answer = answer_part.strip()
                        
                        conversation_parts.append({
                            "question": question,
                            "answer": answer
                        })
                except:
                    # If parsing fails, just keep the original string
                    conversation_parts.append({
                        "raw": agent_entry["conversation"]
                    })
                
                agent_entry["parsed_conversation"] = conversation_parts
            
            user_agents.append(agent_entry)
        
        return {"user_id": user_id, "agents": user_agents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversation-history/{nft_hash}/{user_id}")
async def get_conversation_history(
    nft_hash: str, 
    user_id: str,
    limit: int = 10,
    offset: int = 0
):
    """
    Fetch paginated conversation history for a specific NFT agent.
    Includes filtering by user access permissions.
    """
    try:
        user_id = user_id.lower()  # Normalize user ID
        
        # Check if user has access to this NFT
        if nft_hash not in chat_authorizations:
            raise HTTPException(
                status_code=404,
                detail="NFT hash not found"
            )
        
        auth = chat_authorizations[nft_hash]
        if user_id != auth.creator and user_id not in auth.members:
            raise HTTPException(
                status_code=403,
                detail="User not authorized to access this agent's conversations"
            )
        
        # Get wallet ID for this NFT
        wallet_id = get_wallet_id(nft_hash)
        if wallet_id in ["File not found.", "Error decoding JSON.", "NFT ID not found.", "Empty file."]:
            raise HTTPException(
                status_code=404,
                detail=f"Error retrieving wallet: {wallet_id}"
            )
        
        # Load conversations
        conversations = []
        if os.path.exists('conversations.json'):
            try:
                with open('conversations.json', 'r') as file:
                    data = json.load(file)
                    if wallet_id in data:
                        # Parse conversation string
                        conversation_str = data[wallet_id]
                        
                        # If we have a full conversation history format (assuming it's in JSON)
                        if conversation_str.startswith('[') and conversation_str.endswith(']'):
                            try:
                                conversations = json.loads(conversation_str)
                            except:
                                # Fall back to basic parsing
                                conversations = []
                        else:
                            # Basic parsing of "Question:X,answer: Y" format
                            parts = []
                            current_convo = conversation_str
                            
                            # Split by questions if possible
                            if "Question:" in current_convo:
                                # Handle the typical format "Question:X,answer: Y"
                                try:
                                    question_part = current_convo.split(",answer: ")[0]
                                    answer_part = current_convo.split(",answer: ")[1]
                                    
                                    question = question_part.replace("Question:", "").strip()
                                    answer = answer_part.strip()
                                    
                                    parts.append({
                                        "question": question,
                                        "answer": answer,
                                        "timestamp": None  # We don't have timestamps in current format
                                    })
                                except:
                                    # If parsing fails, add the raw format
                                    parts.append({
                                        "raw": current_convo
                                    })
                            
                            conversations = parts
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error parsing conversations: {str(e)}"
                )
        
        # Get wallet address and agent personality if available
        wallet_address = ""
        personality = {}
        
        wallet_file = f"wallet_storage/{wallet_id}.json"
        if os.path.exists(wallet_file):
            try:
                with open(wallet_file, 'r') as file:
                    wallet_data = json.load(file)
                    if wallet_data.get('addresses') and len(wallet_data['addresses']) > 0:
                        wallet_address = wallet_data['addresses'][0].get('address_id', "")
            except:
                pass
                
        if wallet_address:
            db_file = f"DB/{wallet_address}.json"
            if os.path.exists(db_file):
                try:
                    with open(db_file, 'r') as file:
                        data = json.load(file)
                        personality = {
                            "description": data.get("Personality", ""),
                            "concepts": data.get("Concepts", []),
                            "tools": data.get("Tools", [])
                        }
                except:
                    pass
        
        # Apply pagination if needed
        total_conversations = len(conversations)
        paginated_conversations = conversations[offset:offset+limit] if conversations else []
        
        return {
            "nft_hash": nft_hash,
            "wallet_id": wallet_id,
            "wallet_address": wallet_address,
            "creator": auth.creator,
            "members": auth.members,
            "personality": personality,
            "total_conversations": total_conversations,
            "offset": offset,
            "limit": limit,
            "conversations": paginated_conversations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
