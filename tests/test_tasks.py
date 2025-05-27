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


"""Tests tasks."""

# Note: Use pytest for writing tests!
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.tasks import command


@patch("src.tasks.get_input_files")
@patch("src.tasks.subprocess.run")
@patch("src.tasks.create_output_file")
@patch("src.tasks.create_task_result")
def test_command_with_actual_file_input(
    mock_create_task_result,
    mock_create_output_file,
    mock_subprocess_run,
    mock_get_input_files,
    tmp_path,  # pytest fixture for a temporary directory path
):
    """
    Test the command task with an actual input file from test_data,
    mocking the ssdeep execution.
    """
    # --- Setup: Path to the actual input file ---
    # Assuming pytest runs from the project root (openrelik-worker-ssdeep2)
    project_root = Path(
        __file__
    ).parent.parent  # Gets the 'openrelik-worker-ssdeep2' directory
    actual_input_file_path = project_root / "test_data" / "test.txt"
    assert (
        actual_input_file_path.exists()
    ), f"Test input file not found: {actual_input_file_path}"

    # --- Setup Mocks ---
    workflow_id = "test-workflow-actual-file"
    output_path_val = str(tmp_path)

    # Mock get_input_files to return the actual file's details
    mock_input_file_dict = {
        "path": str(actual_input_file_path),
        "display_name": "test.txt",
        "uuid": "file-uuid-actual",
    }
    mock_get_input_files.return_value = [mock_input_file_dict]

    # Mock subprocess.run for ssdeep
    mock_ssdeep_process = MagicMock()
    mock_ssdeep_process.returncode = 0
    # Define a mock hash for the content of test_data/test.txt
    # The actual hash for "test123OpenRelik\n" (if newline) or "test123OpenRelik"
    # would be different. We are mocking the ssdeep tool's output.
    expected_hash_part = "3:mockedHashForTestFile:"
    mock_ssdeep_process.stdout = f'{expected_hash_part},"{actual_input_file_path.name}"'
    mock_ssdeep_process.stderr = ""
    mock_subprocess_run.return_value = mock_ssdeep_process

    # Mock create_output_file
    expected_output_filename = "SSDeep hash for test.txt.ssdeep"
    expected_output_file_path_obj = tmp_path / expected_output_filename
    mock_output_file_obj = MagicMock()
    mock_output_file_obj.path = str(expected_output_file_path_obj)
    mock_output_file_obj.to_dict.return_value = {
        "path": mock_output_file_obj.path,
        "display_name": "SSDeep hash for test.txt",
    }
    mock_create_output_file.return_value = mock_output_file_obj

    mock_create_task_result.return_value = "mocked_task_result_actual_file"

    # --- Call the task ---
    result = command(
        pipe_result=None,
        input_files=[mock_input_file_dict],
        output_path=output_path_val,
        workflow_id=workflow_id,
        task_config=None,
    )

    # --- Assertions ---
    mock_get_input_files.assert_called_once_with(None, [mock_input_file_dict])
    mock_subprocess_run.assert_called_once_with(
        ["ssdeep", "-s", "-b", str(actual_input_file_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    mock_create_output_file.assert_called_once_with(
        output_path_val,
        display_name="SSDeep hash for test.txt",
        extension="ssdeep",
        data_type="text/plain",
    )

    assert expected_output_file_path_obj.exists()
    assert (
        expected_output_file_path_obj.read_text(encoding="utf-8")
        == expected_hash_part + "\n"
    )

    assert result == "mocked_task_result_actual_file"
