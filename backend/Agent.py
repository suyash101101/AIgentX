from phi.model.ollama import Ollama
from phi.tools.calculator import Calculator
from phi.tools.exa import ExaTools
from phi.tools.file import FileTools
from phi.tools.googlesearch import GoogleSearch
from phi.tools.pandas import PandasTools
from phi.tools.shell import ShellTools
from phi.tools.wikipedia import WikipediaTools
from phi.tools.sleep import Sleep
from dotenv import load_dotenv
from cdp import *
from phi.model.openai.like import OpenAILike
import os
import json
from phi.agent import Agent, RunResponse
from cdp.errors import UnsupportedAssetError
from Creator import ChatbotAnalyzer
from schemas import *

load_dotenv()

API_KEY_NAME = os.environ.get("CDP_API_KEY_NAME")
PRIVATE_KEY = os.environ.get("CDP_PRIVATE_KEY", "").replace('\\n', '\n')
Cdp.configure(API_KEY_NAME, PRIVATE_KEY)

class OnChainAgents:
    def __init__(self, Wallet_Id=None):
        """
        Initializes the OnChainAgents class.

        The constructor checks if a Wallet_Id is provided. If not, it creates a new wallet.
        If a Wallet_Id is given, it attempts to fetch the wallet data associated with that ID.
        
        Parameters:
        Wallet_Id (str): Optional; If provided, attempts to load an existing wallet. 
                         If None, creates a new wallet.
        """
        self.WalletStorage = "wallet_storage"

        if not os.path.exists(self.WalletStorage):
            os.makedirs(self.WalletStorage)
            print(f"Directory '{self.WalletStorage}' created successfully.")

        if Wallet_Id is None:
            self.wallet = Wallet.create()
        else:
            fetched_data = self.fetch(Wallet_Id)
            if fetched_data:
                data = WalletData(wallet_id=fetched_data['wallet_id'], seed=fetched_data['seed'])
                self.wallet = Wallet.import_data(data)
            else:
                raise ValueError(f"Wallet with ID {Wallet_Id} could not be found.")

    def fetch(self, wallet_id):
        """
        Fetches the wallet data from a JSON file.

        This method constructs the file path for the specified wallet ID and attempts to read
        the corresponding JSON file. If the file exists, it loads the data and returns it as a dictionary.

        Parameters:
        wallet_id (str): The ID of the wallet to fetch.

        Returns:
        dict or None: The wallet data dictionary if found, else None.
        """
        file_path = os.path.join(self.WalletStorage, f"{wallet_id}.json")

        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                data_dict = json.load(file)
            print(f"Wallet data for {wallet_id} successfully fetched.")
            return data_dict
        else:
            print(f"No wallet data found for ID: {wallet_id}.")
            return None
        
    def store(self, data_dict):
        """
        Stores the wallet data securely in a JSON file.

        This method takes a dictionary containing wallet data and writes it to a JSON file
        named after the wallet ID. It ensures that the data is saved in a structured format.

        Parameters:
        data_dict (dict): Dictionary containing wallet data.
        """
        wallet_id = data_dict.get("wallet_id")
        file_path = os.path.join(self.WalletStorage, f"{wallet_id}.json")

        with open(file_path, 'w') as file:
            json.dump(data_dict, file)

    def save_wallet(self,data):
        """
        Exports and saves the current wallet's data and seed to files.

        This method exports the current state of the wallet and stores it in JSON format.
        It also saves the seed securely in an encrypted format and logs the wallet ID
        in a separate text file if it does not already exist.

        The process includes checking for existing IDs to prevent duplicates.
        """
        self.store(data.to_dict())
        
        seed_file_path = "my_seed.json"
        self.wallet.save_seed(seed_file_path, encrypt=True)

        wallet_id = data.wallet_id
        id_file_path = "wallet_ids.txt"

        if not self.wallet_id_exists(wallet_id, id_file_path):
            with open(id_file_path, "a") as id_file:
                id_file.write(f"{wallet_id}\n")

    def wallet_id_exists(self, wallet_id, file_path):
        """
        Checks if a given wallet ID exists in the specified text file.

        This method reads through a text file containing existing wallet IDs to determine
        whether the specified ID is present.

        Parameters:
        wallet_id (str): The ID of the wallet to check.
        
        Returns:
        bool: True if the ID exists, False otherwise.
        """
        if os.path.exists(file_path):
            with open(file_path, 'r') as id_file:
                existing_ids = id_file.read().splitlines()
                return wallet_id in existing_ids
        return False

Tools = {
    "Calculator": Calculator(add=True, subtract=True, multiply=True, divide=True, exponentiate=True, factorial=True, is_prime=True, square_root=True),
    "Exa": ExaTools(api_key=os.getenv("EXA_API_KEY")),
    "File": FileTools(),
    "GoogleSearch": GoogleSearch(),
    "Pandas": PandasTools(),
    "Shell": ShellTools(),
    "Wikipedia": WikipediaTools(),
    "Sleep": Sleep()
}
    
def read_json_data(file_path: str) -> dict:
    """
    Reads data from a JSON file and returns it as a dictionary.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The data read from the JSON file, or None if an error occurred.
    """
    try:
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            return data
    except FileNotFoundError:
        print(f"Error: The file {file_path} does not exist.")
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON from the file.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None

def store_mapping(nft_id, wallet_id):
    filename = 'map.json'
    new_entry = {nft_id: wallet_id}
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = {}
    else:
        data = {}
    data.update(new_entry)
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def store_response(wallet_id, prompt, response):
    """Store or update the response for a specific wallet ID in a JSON file."""
    file_path = 'conversations.json'
    print(f"Storing response for wallet_id: {wallet_id}")
    
    # Initialize data dictionary
    data = {}
    
    # Load existing data if the file exists
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as file:
                file_content = file.read().strip()
                
                if file_content:  # Only try to parse if file is not empty
                    try:
                        data = json.loads(file_content)
                        print(f"Successfully loaded existing conversations data")
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON from {file_path}, creating new file")
                        data = {}  # Reset to empty dict if file is corrupt
                else:
                    print(f"Conversations file exists but is empty")
        except Exception as e:
            print(f"Error reading conversations file: {str(e)}")
            # Continue with empty data dictionary
    
    # Update the response for the specified wallet ID
    data[wallet_id] = f"Question:{prompt},answer: {response}"
    print(f"Updated conversation data for wallet_id: {wallet_id}")
    
    # Write the updated data back to the JSON file
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
        print(f"Successfully wrote conversation data to {file_path}")
    except Exception as e:
        print(f"Error writing conversation data: {str(e)}")

def get_wallet_id(nft_id):
    filename = 'map.json'
    print(f"Attempting to get wallet_id for NFT: {nft_id}")
    try:
        if not os.path.exists(filename):
            print(f"Warning: {filename} does not exist")
            return "File not found."
        
        with open(filename, 'r') as file:
            file_content = file.read().strip()
            print(f"map.json content: '{file_content[:100]}'")  # Print first 100 chars for debugging
            
            if not file_content:
                print(f"Warning: {filename} is empty")
                return "Empty file."
            
            # Try to fix malformed JSON if possible
            try:
                # First attempt - try to load as is
                data = json.loads(file_content)
            except json.JSONDecodeError:
                print("Initial JSON decode failed, attempting to fix JSON format")
                
                # Second attempt - try to fix common JSON issues
                if file_content.startswith('\ufeff'):  # BOM character
                    print("Removing BOM character")
                    file_content = file_content[1:]
                
                # Try again with cleaned content
                try:
                    data = json.loads(file_content)
                    print("Successfully loaded JSON after cleanup")
                except json.JSONDecodeError:
                    # If we can't fix it, create a new empty mapping
                    print(f"Could not parse {filename} - creating new empty mapping")
                    data = {}
                    # Write the empty mapping back to the file to fix it for next time
                    with open(filename, 'w') as write_file:
                        json.dump(data, write_file, indent=4)
            
        if nft_id in data:
            wallet_id = data[nft_id]
            print(f"Found wallet_id: {wallet_id} for NFT: {nft_id}")
            return wallet_id
        else:
            print(f"NFT ID {nft_id} not found in mapping")
            return "NFT ID not found."
    except FileNotFoundError:
        print(f"Error: {filename} not found")
        return "File not found."
    except Exception as e:
        print(f"Unexpected error in get_wallet_id: {str(e)}")
        return f"Error: {str(e)}"

def get_last_conversation(wallet_id):
    """Retrieve the last conversation for a specific wallet ID from conversations.json."""
    file_path = 'conversations.json'
    
    # Check if file exists first
    if not os.path.exists(file_path):
        return "not there. This is your first conversation."
    
    try:
        # Attempt to read the JSON data from the file
        with open(file_path, 'r') as file:
            data = json.load(file)
            # Check if the wallet ID exists in the data
            if wallet_id in data:
                return data[wallet_id]
            else:
                return "not there. This is your first conversation."
    except json.JSONDecodeError:
        # Handle case where file exists but contains invalid JSON
        return "not there. This is your first conversation."

def load_agent(NFT_id, prompt):
    try:
        print(f"Starting load_agent for NFT_id: {NFT_id}")
        wallet_id = get_wallet_id(NFT_id)
        print(f"Retrieved wallet_id: {wallet_id}")
        
        if wallet_id in ["File not found.", "Error decoding JSON.", "NFT ID not found.", "Empty file."]:
            print(f"Error retrieving wallet_id: {wallet_id}")
            return agentInteractResponse(
                response=f"Error: {wallet_id}",
                isMetaMask=False,
                walletAddress="unknown",
                value=None,
                Responses=0
            )
        
        convo = get_last_conversation(wallet_id)
        print(f"Retrieved conversation history. Length: {len(convo) if convo else 0}")
        
        agent = OnChainAgents(Wallet_Id=wallet_id)
        print(f"Created OnChainAgents with wallet address: {agent.wallet.default_address.address_id}")
        
        file_path = f"DB/{agent.wallet.default_address.address_id}.json"
        print(f"Attempting to read data from: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} does not exist")
            return agentInteractResponse(
                response=f"Error: Agent configuration file not found.",
                isMetaMask=False,
                walletAddress=agent.wallet.default_address.address_id,
                value=None,
                Responses=0
            )
            
        data = read_json_data(file_path)
        print(f"Data loaded: {data is not None}")
        
        if not data:
            print(f"Error: Failed to load data from {file_path}")
            return agentInteractResponse(
                response="Error: Failed to load agent configuration.",
                isMetaMask=False,
                walletAddress=agent.wallet.default_address.address_id,
                value=None,
                Responses=0
            )
            
        def get_balance(asset_id) -> str:
            """
            Get the balance of a specific asset in the agent's wallet.
            
            Parameters:
            asset_id (str): Asset identifier ("eth", "usdc") or contract address of an ERC-20 token
            
            Returns:
            str: A message showing the current balance of the specified asset.
            """
            balance = agent.wallet.balance(asset_id)
            return f"Current balance of {asset_id}: {balance}"

        def transfer_asset(amount, asset_id, destination_address):
            """
            Transfer an asset to a specific address.
            
            Parameters:
            amount (Union[int, float, Decimal]): Amount to transfer.
            asset_id (str): Asset identifier ("eth", "usdc") or contract address of an ERC-20 token.
            destination_address (str): Recipient's address.
            
            Returns:
            str: A message confirming the transfer or describing an error.
            """
            try:
                is_mainnet = agent.wallet.network_id == "base-mainnet"
                is_usdc = asset_id.lower() == "usdc"
                gasless = is_mainnet and is_usdc
                if asset_id.lower() in ["eth", "usdc"]:
                    transfer = agent.wallet.transfer(amount,
                                                    asset_id,
                                                    destination_address,
                                                    gasless=gasless)
                    transfer.wait()
                    gasless_msg = " (gasless)" if gasless else ""
                    return f"Transferred {amount} {asset_id}{gasless_msg} to {destination_address}"
                
                try:
                    balance = agent.wallet.balance(asset_id)
                except UnsupportedAssetError:
                    return f"Error: The asset {asset_id} is not supported on this network. It may have been recently deployed. Please try again in about 30 minutes."

                if balance < amount:
                    return f"Insufficient balance. You have {balance} {asset_id}, but tried to transfer {amount}."

                transfer = agent.wallet.transfer(amount, asset_id, destination_address)
                transfer.wait()
                return f"Transferred {amount} {asset_id} to {destination_address}"
                
            except Exception as e:
                return f"Error transferring asset: {str(e)}. If this is a custom token, it may have been recently deployed. Please try again in about 30 minutes, as it needs to be indexed by CDP first."

        ToolKit = []
        if data:
            for key in data["Tools"]:
                if key in Tools.keys():
                    ToolKit.append(Tools[key])
                    
        print(f"Setting up agent with {len(ToolKit)} tools")
        
        try:
            based_agent = Agent(
                model=OpenAILike(id="llama3.1:70b",api_key=os.getenv("GALADRIAL_API_KEY"),base_url="https://api.galadriel.com/v1"),
                tools=[get_balance, transfer_asset, ExaTools(api_key=os.getenv("EXA_API_KEY"))]+ToolKit,
                description=data["Personality"]+f"You have very in depth knowledge in the fields of {data['Concepts']}",
                instructions=[
                    "Always display the balance when asked.",
                    "As long as the prompt is not about transactions or balance, the answer should be long, thorough and based on the personality.",
                    "Make sure that when you speak you are speaking according to your personality and as if you are in the middle of a conversation with the other person. Make sure there is a flow.",
                    "Make the conversation as interactive and socaial as possible.",
                    "Always search for real time data on the question asked and then answer.",
                    f"Your last conversation was {convo}.",
                    "Make sure you dont break the flow."
                ]
            )
            print("Agent initialized successfully")
            
            run: RunResponse = based_agent.run(prompt)
            print("Agent run completed successfully")
            
            try:
                store_response(wallet_id, prompt, run.content)
                print("Response stored successfully")
            except Exception as e:
                print(f"Error storing response: {str(e)}")
                # Continue even if storage fails
            
            return agentInteractResponse(
                response=run.content,
                isMetaMask=False,
                walletAddress=agent.wallet.default_address.address_id,
                value=None,
                Responses=0
            )
        except Exception as e:
            print(f"Error in agent setup or execution: {str(e)}")
            return agentInteractResponse(
                response=f"Error processing your request: {str(e)}",
                isMetaMask=False,
                walletAddress=agent.wallet.default_address.address_id if agent and hasattr(agent, 'wallet') else "unknown",
                value=None,
                Responses=0
            )
    except Exception as e:
        print(f"Unexpected error in load_agent: {str(e)}")
        return agentInteractResponse(
            response=f"An unexpected error occurred: {str(e)}",
            isMetaMask=False,
            walletAddress="unknown",
            value=None,
            Responses=0
        )

def CreateAgent(prompt,NFT_id):
    agent = OnChainAgents()
    print("hi1")
    data = agent.wallet.export_data()
    print("hi2")
    creater = ChatbotAnalyzer()
    print("hi3")
    tools, concepts = creater.find_tools_and_concepts(prompt)
    print("hi4")
    personality = creater.GeneratePersonality(prompt)
    print("hi5")
    instructions = creater.GenerateInstructions(prompt)
    print("hi6")
    creater.save_to_json(tools, personality, instructions, concepts,agent.wallet.default_address.address_id)
    print("hi7")
    store_mapping(NFT_id,data.wallet_id)
    print("hi8")
    agent.save_wallet(data)
    print("hi9")
    return walletAddress(walletAddress=agent.wallet.default_address.address_id)

# load_agent("123","What did I ask you in the previous conversation.")