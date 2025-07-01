import sys
import traceback

from .storage import retrieve_agents
from .storage.index import pending_storage


async def execute_agent(agent_name: str, json_data: any, kwargs: dict = {}) -> any:
    try:
        agents = retrieve_agents()

        # If not found in approved, check pending
        if agent_name not in agents:
            pending_response = pending_storage.get_all_agents()
            if (
                pending_response.get("success")
                and pending_response.get("data")
                and agent_name in pending_response["data"]
            ):
                agents = pending_response["data"]

        if agent_name in agents:
            agent_code = agents[agent_name]["code"]
            print("📝 Executing code:", agent_code)
            print("📦 With kwargs:", kwargs)
            # print("📊 Dataset sample:", json_data[:2])

            # Prepare a local scope dictionary
            local_scope = {}

            # Inject the agent code (defines a function)
            exec(agent_code, {}, local_scope)

            # Extract the actual function
            function_name = next(iter(local_scope))
            func = local_scope[function_name]

            # Run the function
            result = func(json_data, kwargs)
            print("🔍 Created function:", func)
            print("✨ Function result:", result)
            return result

        else:
            return "Agent not found."

    except Exception as error:
        print("❌ Error in execution:", str(error))
        traceback.print_exc(file=sys.stdout)
        return f"Error executing agent: {str(error)}"
