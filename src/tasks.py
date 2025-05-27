# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import logging

from openrelik_worker_common.file_utils import create_output_file
from openrelik_worker_common.task_utils import create_task_result, get_input_files

from .app import celery

# Task name used to register and route the task to the correct queue.
# This name should be unique and is used by Celery to identify the task.
TASK_NAME = "openrelik-worker-ssdeep.tasks.calculate_ssdeep_hash"

# Task metadata for registration in the core system.
TASK_METADATA = {
    "display_name": "SSDeep Hash Calculation",
    "description": (
        "Calculates the SSDeep (context-triggered piecewise hash) for each input file. "
        "Output is a text file per input, containing the hash or an error/notice."
    ),
    "task_config": [],  # No user-configurable options for basic hashing.
}


@celery.task(bind=True, name=TASK_NAME, metadata=TASK_METADATA)
def command(
    self,
    pipe_result: str = None,
    input_files: list = None,
    output_path: str = None,
    workflow_id: str = None,
    task_config: dict = None,
) -> str:
    """Calculates the SSDeep hash for input files.

    Args:
        pipe_result: Base64-encoded result from the previous Celery task, if any.
        input_files: List of input file dictionaries (unused if pipe_result exists).
        output_path: Path to the output directory.
        workflow_id: ID of the workflow.
        task_config: User configuration for the task.

    Returns:
        Base64-encoded dictionary containing task results.
    """
    log = self.get_logger()

    input_files = get_input_files(pipe_result, input_files or [])
    output_files = []
    # General command string for reporting purposes in the task result.
    base_command_for_reporting = "ssdeep -s -b"

    if not input_files:
        return create_task_result(
            output_files=[],
            workflow_id=workflow_id,
            command=base_command_for_reporting,
            meta={"message": "No input files provided to calculate SSDeep hash."},
        )

    for input_file_dict in input_files:
        input_file_path = input_file_dict.get("path")
        input_file_display_name = input_file_dict.get(
            "display_name", input_file_dict.get("filename", "input_file")
        )

        if not input_file_path:
            log.warning(f"Skipping file entry with no path: {input_file_dict}")
            continue

        # Run the command
        # -s: Silent mode (suppresses errors to stderr, prints them to stdout)
        # -b: Bare mode (strips directory paths from filename in output, if any)
        cmd_to_run = ["ssdeep", "-s", "-b", input_file_path]

        process = subprocess.run(
            cmd_to_run, capture_output=True, text=True, check=False
        )
        ssdeep_result_text = process.stdout.strip()
        ssdeep_hash_or_error: str

        if process.returncode != 0:
            # This might capture other errors if -s doesn't suppress everything
            error_details = process.stderr.strip() or ssdeep_result_text
            ssdeep_hash_or_error = (
                f"Error running ssdeep (code {process.returncode}): " f"{error_details}"
            )
            log.error(f"SSDeep failed for {input_file_path}: {ssdeep_hash_or_error}")

        elif (
            ',"' in ssdeep_result_text
        ):  # Expected format for a successful hash: HASH,"FILENAME"
            ssdeep_hash_or_error = ssdeep_result_text.split(',"', 1)[0]
        else:  # Likely "file too small" or other message from ssdeep printed to stdout
            ssdeep_hash_or_error = f"SSDeep notice: {ssdeep_result_text}"

        # Create an output file to store the hash or message
        output_file_obj = create_output_file(
            output_path,  # Pass output_path as a positional argument
            display_name=f"SSDeep hash for {input_file_display_name}",
            extension="ssdeep",
            data_type="text/plain",  # Content is the ssdeep hash string or a notice
        )

        with open(output_file_obj.path, "w", encoding="utf-8") as fh:
            fh.write(ssdeep_hash_or_error + "\n")

        output_files.append(output_file_obj.to_dict())

    if (
        not output_files and input_files
    ):  # Processed inputs but no outputs (e.g. all files failed path validation)
        # This specific error might be too generic if individual file errors
        # are already captured in their output files.
        # Depending on desired behavior, this could be a warning or info log.
        log.warning(
            "SSDeep task processed input files but generated no output files overall."
        )

    return create_task_result(
        output_files=output_files,
        workflow_id=workflow_id,
        command=base_command_for_reporting,  # General command used
        meta={},  # No additional metadata for the overall task result in this case
    )
