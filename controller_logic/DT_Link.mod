MODULE Module1

    ! === Persistent Variables Exposed via OPC UA ===
    ! --- From MotionCommand.json ---
    PERS string CommandType := "";
    PERS string JointTarget := "";
    PERS string Speed := "";
    PERS string Zone := "";
    PERS string Tool := "";
    PERS string WorkObject := "";
    PERS string CommandID := "";
    PERS string Timestamp := "";

    ! --- From ExecutionStatus.json ---
    PERS bool CommandAcknowledged := FALSE;
    PERS bool ExecutionStarted := FALSE;
    PERS bool ExecutionCompleted := FALSE;
    PERS bool ErrorState := FALSE;
    PERS string LastUpdate := "";

    ! === Local Variables ===
    VAR string lastCommandID := "";
    VAR string newCommandID := "";
    VAR num loopDelayMs := 100;  ! milliseconds

    ! === Main Execution Loop ===
    PROC main()
        WHILE TRUE DO

            ! Read the current incoming command
            newCommandID := CommandID;

            ! === Detect a New Command ===
            IF (newCommandID <> lastCommandID) AND (newCommandID <> "") THEN
                TPWrite " Received command ID: " + newCommandID;

                ! Step 1: Acknowledge command
                CommandAcknowledged := TRUE;

                ! Step 2: Start execution
                ExecutionStarted := TRUE;
                ExecutionCompleted := FALSE;
                ErrorState := FALSE;

                ! Simulate motion or execution logic
                TPWrite "Executing " + CommandType + " with target " + JointTarget;
                WaitTime 1.0;  ! simulate execution time

                ! Step 3: Complete execution
                ExecutionCompleted := TRUE;
                ExecutionStarted := FALSE;
                CommandAcknowledged := FALSE;

                ! Write semantic timestamp (mocked)
                LastUpdate := "2025-05-31T20:00:00Z";

                ! Store command ID to prevent repeated execution
                lastCommandID := newCommandID;
            ENDIF

            ! === Do NOT clear CommandID here ===
            ! Python client must reset ExecutionCompleted = FALSE before sending next command

            WaitTime loopDelayMs / 1000;
        ENDWHILE
    ENDPROC

ENDMODULE