# Semantic Interoperability Framework for Digital Twin-Based Virtual Commissioning of Robotic Assembly in Industrialized Construction

Supplementary repository for:

> Gallopp Ramírez, Ricardo A., Alwisy, Aladdin, & Issa, Raja R. A. (2026). Semantic interoperability
> framework for digital twin-based virtual commissioning of robotic assembly in
> industrialized construction. _Automation in Construction_, 190, 107095.
> https://doi.org/10.1016/j.autcon.2026.107095

---

## Repository Structure

```text
dtvcframework/
├── README.md
├── LICENSE
├── CITATION.cff
├── aas_models/
│   ├── ExecutionStatus.json
│   ├── JointTrajectoryLog.json
│   └── MotionCommand.json
├── controller_logic/
│   └── DT_Link.mod
└── src/
    └── baseline_logger.py
```
---

## AAS Submodel Overview

Three submodels define the semantic data exchange layer of the framework:

| Submodel             | Role                                                                           |
| :------------------- | :----------------------------------------------------------------------------- |
| `MotionCommand`      | Encodes execution-time motion instructions from the DT to the robot controller |
| `ExecutionStatus`    | Captures controller feedback and completion state flags                        |
| `JointTrajectoryLog` | Stores semantically structured execution trace data per command cycle          |

The `CommandID` field is the linking key across all three submodels and the RAPID module, ensuring traceability across the full supervisory semantic loop.

---

## Controller Logic 

`DT_Link.mod` is an ABB RAPID module that declares Persistent Variables (PERS) corresponding to fields defined in the `MotionCommand` and `ExecutionStatus` submodels. These variables are exposed as OPC UA nodes, forming the semantic communication bridge between the DT and the virtual IRC5 controller.

The module implements the three-step command handshake:

1. **Acknowledge** — sets `CommandAcknowledged = TRUE` upon detecting a new `CommandID`
2. **Execute** — sets `ExecutionStarted = TRUE`, runs motion logic, then sets `ExecutionCompleted = TRUE`
3. **Reset** — clears acknowledge and started flags; the Python orchestration client must reset `ExecutionCompleted = FALSE` before issuing the next command

---

## System Requirements & Setup

This framework requires an Asset Administration Shell server to host the submodels. **Eclipse BaSyx** was deployed via Docker.

### 1. AAS Server Initialization

Initialize the server using Docker:

```bash
docker pull eclipsebasyx/aas-server:latest
docker run -p 8081:8081 eclipsebasyx/aas-server:latest
```

### 2. AAS Repository

The orchestrator interacts via BaSyx REST API (PUT/GET) to update `ExecutionStatus` and `JointTrajectoryLog` submodels during execution.

### 3. Submodel Initialization

Initialize the AAS environment with your submodel IDs before running:

- `urn:submodel:motioncommand:001`
- `urn:submodel:executionstatus:001`
- `urn:submodel:jointtrajectorylog:001`

### 4. OPC UA Connection

`DT_Link.mod` must be loaded and running in the RAPID task on the ABB IRC5
controller. OPC UA endpoint URLs, node IDs, namespace indices, and certificates
are environment-specific and must be configured locally.

---

## Baseline Logger — `src/baseline_logger.py`

`baseline_logger.py` demonstrates the structural pattern for:

- Connecting to an OPC UA server
- Reading `ExecutionStatus` submodel fields
- Writing logged data to the BaSyx AAS Repository via REST

---

## What Is Not Included

The following are withheld to protect ongoing research:

- Full orchestration script with live OPC UA subscriptions and BaSyx REST calls
- Real OPC UA endpoint URLs, namespace indices, and node mappings
- Robot station file (`.rspag`) and USD scene assets
- cuRobo motion planning scripts

---

## Citation

See `CITATION.cff` for the full citation record.

---

## License

This repository is released under the MIT License. See `LICENSE` for details.
