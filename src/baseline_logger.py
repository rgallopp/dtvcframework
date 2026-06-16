"""
baseline_logger.py
==================
Structural baseline for the supervisory closed-loop orchestration.
Demonstrates semantic data exchange across three AAS submodels:
MotionCommand, ExecutionStatus, and JointTrajectoryLog.

Does NOT include real OPC UA endpoints, node identifiers, or
controller-specific configuration.

Execution flow:
    1.  Subscribe to ExecutionCompleted node 
    2.  Reset ExecutionCompleted = FALSE before dispatching next command
    3.  Write MotionCommand fields to OPC UA nodes
    4.  ABB IoT Gateway updates RAPID PERS variables on IRC5 
    5.  IRC5 executes motion via DT_Link.mod 
    6.  Controller sets ExecutionCompleted = TRUE on completion 
    7.  Python client receives data-change event, unblocks async wait
    8.  Push ExecutionStatus to BaSyx 
    9.  Append timestamped entry to JointTrajectoryLog 

AAS submodel files (relative to src/):
    ../aas_models/MotionCommand.json
    ../aas_models/ExecutionStatus.json
    ../aas_models/JointTrajectoryLog.json

Controller logic:
    ../controller_logic/DT_Link.mod

Dependencies:
    asyncua, requests, asyncio

Author: Ricardo A. Gallopp Ramírez — rgalloppr@ufl.edu
"""

import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration — replace placeholder values with your environment settings
# ---------------------------------------------------------------------------

# OPC UA connection (production values intentionally omitted)
OPCUA_URL: str = "opc.tcp://<host>:<port>/<server-name>"
APP_URI: str = "urn:<hostname>:client"
CERT_PATH: str = "certificate.pem"
KEY_PATH: str = "private_key.pem"

# Base OPC UA node path — controller-specific; omitted intentionally.
BASE_NODE: str = "ns=<namespace>;s=<your-node-path>/"

# AAS Host — Eclipse BaSyx REST API base URL
AAS_BASE_URL: str = "http://localhost:8081/submodels"

# Submodel identifiers — must match your AAS registry entries
EXECUTION_STATUS_ID: str = "urn:submodel:executionstatus:001"
JOINT_TRAJECTORY_LOG_ID: str = "urn:submodel:jointtrajectorylog:001"

# Orchestration
NUM_ITERATIONS: int = 20

# Path to MotionCommand submodel JSON, relative to this script's location.
MOTION_COMMAND_FILE: Path = Path(__file__).parent / ".." / "aas_models" / "MotionCommand.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def encode_submodel_id(submodel_id: str) -> str:
    """
    Base64url-encode a submodel ID for use in BaSyx REST API path segments.
    Trailing '=' padding is stripped per the AAS specification.
    """
    return base64.urlsafe_b64encode(submodel_id.encode()).decode().rstrip("=")


def aas_endpoint(submodel_id: str) -> str:
    """Return the full REST endpoint URL for a given submodel ID."""
    return f"{AAS_BASE_URL}/{encode_submodel_id(submodel_id)}"


def utc_now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def make_aas_property(
    id_short: str,
    value: Any,
    value_type: str = "xs:string",
) -> dict:
    """
    Construct a minimal AAS Property element compliant with the
    AAS metamodel.

    Args:
        id_short:    The idShort identifier for this property.
        value:       The property value.
        value_type:  XSD type string (default: xs:string).

    Returns:
        A dict representing a single AAS Property element.
    """
    return {
        "modelType": "Property",
        "idShort": id_short,
        "valueType": value_type,
        "value": value,
    }


# ---------------------------------------------------------------------------
# MotionCommand — load from AAS-compliant JSON
# ---------------------------------------------------------------------------

def load_motion_command(filepath: Path) -> dict:
    """
    Parse the MotionCommand AAS submodel JSON and return a flat field map
    keyed by idShort.

    Args:
        filepath: Path to MotionCommand.json.

    Returns:
        Dict mapping each idShort to its value.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = json.load(f)

    fields: dict = {element["idShort"]: element["value"] for element in raw["elements"]}

    # Normalize CommandID to string — JSON may store it as int (e.g. 1001)
    if "CommandID" in fields:
        fields["CommandID"] = str(fields["CommandID"])

    logger.info("MotionCommand loaded — CommandID: %s", fields.get("CommandID"))
    return fields


# ---------------------------------------------------------------------------
# OPC UA interaction (mocked — replace with asyncua calls in production)
# ---------------------------------------------------------------------------

async def opcua_subscribe_execution_completed() -> None:
    """
    Subscribe to the ExecutionCompleted OPC UA node.

    Production:
        handler = EventHandler()
        subscription = await client.create_subscription(100, handler)
        exec_node = client.get_node(BASE_NODE + "ExecutionCompleted")
        await subscription.subscribe_data_change(exec_node)
    """
    logger.info("[OPC UA] Subscribed to ExecutionCompleted (event-driven)")
    await asyncio.sleep(0)  # yield — replace with real subscription setup


async def opcua_reset_execution_flag() -> None:
    """
    Reset ExecutionCompleted = FALSE on the OPC UA server
    before dispatching a new command.

    Production:
        await exec_node.write_value(False)
        await asyncio.sleep(0.1)
    """
    logger.info("[OPC UA] Reset ExecutionCompleted = FALSE")
    await asyncio.sleep(0)  # yield — replace with real node write


async def opcua_write_motion_fields(fields: dict) -> None:
    """
    Write MotionCommand submodel fields to OPC UA nodes.

    Each field maps directly to a RAPID PERS variable declared in DT_Link.mod
    and exposed as an OPC UA node by the ABB IoT Gateway add-on. List values
    (JointTarget) are serialized to bracket-notation strings matching the
    RAPID string type declaration.

    Production:
        for key, val in fields.items():
            serialized = (
                "[" + ", ".join(map(str, val)) + "]"
                if isinstance(val, list)
                else str(val)
            )
            await node_map[key].write_value(serialized)

    Args:
        fields: MotionCommand field map from load_motion_command().
    """
    for key, val in fields.items():
        logger.info("[OPC UA] Write  %-20s = %s", key, val)
    await asyncio.sleep(0)  # yield — replace with real node writes


async def opcua_wait_for_execution_completed(command_id: str) -> None:
    """
    Block asynchronously until the virtual IRC5
    controller signals ExecutionCompleted = TRUE via OPC UA data-change
    event, then unblock.

    Production:
        handler.event.clear()
        await handler.event.wait()   # wrapped in asyncio.wait_for in the loop

    Args:
        command_id: CommandID of the dispatched command, used for logging.
    """
    logger.info("[OPC UA] Awaiting ExecutionCompleted event — CommandID: %s", command_id)
    await asyncio.sleep(0.05)  # simulated controller latency — replace with event wait
    logger.info("[OPC UA] ExecutionCompleted received    — CommandID: %s", command_id)


async def opcua_read_execution_status_vars() -> dict:
    """
    Read the four Boolean execution-state variables from the OPC UA server
    after ExecutionCompleted fires.

    These variables are declared as RAPID PERS bools in DT_Link.mod and
    exposed as OPC UA nodes via the ABB IoT Gateway add-on. Their post-
    execution state (set by DT_Link.mod) is:
        CommandAcknowledged : False  (cleared after completion)
        ExecutionStarted    : False  (cleared after completion)
        ExecutionCompleted  : True   (set on completion)
        ErrorState          : False  (no fault)

    Production:
        status = {}
        for var in ["CommandAcknowledged", "ExecutionStarted",
                    "ExecutionCompleted", "ErrorState"]:
            status[var] = await client.get_node(BASE_NODE + var).read_value()
        return status

    Returns:
        Dict mapping each variable name to its Boolean value.
    """
    # Mock values reflect the post-execution PERS state set by DT_Link.mod
    return {
        "CommandAcknowledged": False,
        "ExecutionStarted": False,
        "ExecutionCompleted": True,
        "ErrorState": False,
    }


# ---------------------------------------------------------------------------
# AAS submodel updates via Eclipse BaSyx REST API
# ---------------------------------------------------------------------------

def push_execution_status(
    command_id: str,
    status_vars: dict,
    timestamp: str,
) -> None:
    """
    Push the ExecutionStatus AAS submodel to the BaSyx
    REST API via HTTP PUT.

    Submodel fields:
        CommandAcknowledged : bool     — Controller received the command
        ExecutionStarted    : bool     — Motion routine has begun
        ExecutionCompleted  : bool     — Motion routine finished successfully
        ErrorState          : bool     — Fault flag from the controller
        LastUpdate          : dateTime — Timestamp of this status record

    Args:
        command_id:   CommandID of the dispatched motion command.
        status_vars:  Boolean OPC UA variable readings from the controller.
        timestamp:    UTC timestamp string for LastUpdate.
    """
    endpoint = aas_endpoint(EXECUTION_STATUS_ID)

    submodel_elements = [
        make_aas_property(var, val, "xs:boolean")
        for var, val in status_vars.items()
    ]
    submodel_elements.append(make_aas_property("LastUpdate", timestamp, "xs:dateTime"))
    submodel_elements.append(make_aas_property("CommandID", command_id))

    payload = {
        "modelType": "Submodel",
        "kind": "Instance",
        "idShort": "ExecutionStatus",
        "id": EXECUTION_STATUS_ID,
        "semanticId": {
            "type": "ExternalReference",
            "keys": [{
                "type": "GlobalReference",
                "value": "https://example.org/semantics/ExecutionStatus",
            }],
        },
        "submodelElements": submodel_elements,
    }

    logger.info("[AAS] PUT ExecutionStatus — CommandID: %s  -> %s", command_id, endpoint)
    # Production: response = requests.put(endpoint, json=payload, timeout=5)
    logger.debug("[AAS] Payload:\n%s", json.dumps(payload, indent=2))


def append_joint_trajectory_log(
    command_id: str,
    joint_values: list,
    timestamp: str,
) -> None:
    """
    Append a timestamped execution entry to the
    JointTrajectoryLog AAS submodel via HTTP PUT to individual
    submodel-element endpoints on the BaSyx REST API.

    Submodel fields:
        CommandID            : string — Links this entry to its MotionCommand
        ExecutedJointTarget  : string — JSON-serialized joint-space configuration (double[])
        ExecutionTimestamp   : string — UTC timestamp of the execution event
        Status               : string — Execution outcome (e.g. "Completed")

    Args:
        command_id:   CommandID of the completed execution cycle.
        joint_values: Joint configuration recorded during execution.
        timestamp:    UTC timestamp of the execution event.
    """
    base_endpoint = f"{aas_endpoint(JOINT_TRAJECTORY_LOG_ID)}/submodel-elements"

    entries = [
        make_aas_property("CommandID", command_id),
        make_aas_property("ExecutedJointTarget", json.dumps(joint_values)),
        make_aas_property("ExecutionTimestamp", timestamp, "xs:dateTime"),
        make_aas_property("Status", "Completed"),
    ]

    for entry in entries:
        url = f"{base_endpoint}/{entry['idShort']}"
        logger.info(
            "[AAS] PUT JointTrajectoryLog.%-20s — CommandID: %s  -> %s",
            entry["idShort"], command_id, url,
        )
        # Production: response = requests.put(url, json=entry, timeout=5)
        logger.debug("[AAS] Payload: %s", json.dumps(entry))


# ---------------------------------------------------------------------------
# Main orchestration loop
# ---------------------------------------------------------------------------

async def supervisory_orchestration_loop() -> None:
    """
    Event-driven supervisory closed-loop orchestration. 
    """
    fields = load_motion_command(MOTION_COMMAND_FILE)
    joint_values: list = fields.get("JointTarget", [])

    # Step 1: Subscribe to ExecutionCompleted — once, before the loop
    # Production: connect OPC UA client here, then subscribe
    await opcua_subscribe_execution_completed()

    logger.info("Starting supervisory orchestration — %d iterations", NUM_ITERATIONS)

    for i in range(NUM_ITERATIONS):
        command_id = f"cmd_{i + 1:04d}"
        timestamp = utc_now()
        logger.info(
            "--- Iteration %d / %d  CommandID: %s ---",
            i + 1, NUM_ITERATIONS, command_id,
        )

        # Step 2: Reset ExecutionCompleted = FALSE before dispatching
        await opcua_reset_execution_flag()

        # Step 3: Write MotionCommand fields to OPC UA nodes
        await opcua_write_motion_fields(
            {**fields, "CommandID": command_id, "Timestamp": timestamp}
        )

        # Steps 4–7: Await event-driven ExecutionCompleted signal from controller
        try:
            await asyncio.wait_for(
                opcua_wait_for_execution_completed(command_id),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.error(
                "Timeout waiting for ExecutionCompleted — CommandID: %s", command_id
            )
            continue

        # Step 8: Read execution status vars and push ExecutionStatus to AAS
        status_vars = await opcua_read_execution_status_vars()
        push_execution_status(command_id, status_vars, timestamp)

        # Step 9: Append joint trajectory record to JointTrajectoryLog
        append_joint_trajectory_log(command_id, joint_values, timestamp)

    logger.info("Orchestration complete — %d iterations dispatched.", NUM_ITERATIONS)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(supervisory_orchestration_loop())