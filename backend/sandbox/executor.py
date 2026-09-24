import os
import re
import asyncio
import tempfile
import subprocess
from models.schemas import CodeFile, TestResult
from config import settings


class SandboxExecutor:
    """Executes code safely in a Docker container or locally as fallback."""

    IMAGE_NAME = "ai-engineer-sandbox"

    def __init__(self):
        self.timeout = settings.SANDBOX_TIMEOUT
        self._docker_available = None

    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        if self._docker_available is not None:
            return self._docker_available
        try:
            result = subprocess.run(
                ["docker", "info"], capture_output=True, timeout=5
            )
            self._docker_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._docker_available = False
        return self._docker_available

    async def execute_code(self, code_files: list[CodeFile], command: str) -> dict:
        """
        Write code files to a temp directory and execute command.
        Uses Docker if available, otherwise runs locally.
        Returns stdout, stderr, and exit code.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_sync, code_files, command)

    def _execute_sync(self, code_files: list[CodeFile], command: str) -> dict:
        """Synchronous execution wrapper."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write all code files, guarding against path traversal
            for file in code_files:
                # Strip leading slashes so os.path.join can't escape tmpdir
                safe_rel = file.path.lstrip("/")
                file_path = os.path.realpath(os.path.join(tmpdir, safe_rel))
                if not file_path.startswith(os.path.realpath(tmpdir) + os.sep):
                    continue  # skip any path that escapes the sandbox
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(file.content)

            if self._check_docker():
                return self._execute_in_docker(tmpdir, command)
            else:
                return self._execute_locally(tmpdir, command)

    def _execute_in_docker(self, workdir: str, command: str) -> dict:
        """Execute in Docker container with security limits."""
        try:
            result = subprocess.run(
                [
                    "docker", "run",
                    "--rm",
                    "--network=none",
                    "--memory=256m",
                    "--cpus=0.5",
                    "--pids-limit=50",
                    "-v", f"{workdir}:/workspace",
                    "-w", "/workspace",
                    self.IMAGE_NAME,
                    "bash", "-c", command,
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
                "engine": "docker",
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Execution timed out",
                "exit_code": -1,
                "success": False,
                "engine": "docker",
            }

    def _execute_locally(self, workdir: str, command: str) -> dict:
        """Fallback: execute locally if Docker is not available."""
        try:
            result = subprocess.run(
                ["bash", "-c", command],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=workdir,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
                "engine": "local",
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Execution timed out",
                "exit_code": -1,
                "success": False,
                "engine": "local",
            }

    def parse_pytest_output(self, output: str) -> list[TestResult]:
        """Parse pytest output into structured test results."""
        results = []
        lines = output.strip().split("\n")

        for line in lines:
            # Match pytest's output format: test_file.py::test_name PASSED/FAILED
            if " PASSED" in line or " FAILED" in line or " ERROR" in line:
                parts = line.strip().split(" ")
                test_name = parts[0] if parts else line
                passed = "PASSED" in line
                results.append(TestResult(
                    test_name=test_name,
                    passed=passed,
                    output=line.strip(),
                    error=None if passed else line.strip(),
                ))

        # If no structured output found, create a summary result
        if not results:
            has_error = "error" in output.lower() or "failed" in output.lower() or "Error" in output
            # Check for "X passed" pattern
            if "passed" in output.lower():
                match = re.search(r"(\d+) passed", output)
                if match:
                    count = int(match.group(1))
                    for i in range(count):
                        results.append(TestResult(
                            test_name=f"test_{i+1}",
                            passed=True,
                            output=f"Test {i+1} passed",
                        ))
                fail_match = re.search(r"(\d+) failed", output)
                if fail_match:
                    count = int(fail_match.group(1))
                    for i in range(count):
                        results.append(TestResult(
                            test_name=f"test_failed_{i+1}",
                            passed=False,
                            output="Test failed",
                            error=output[-500:] if len(output) > 500 else output,
                        ))
            elif has_error:
                results.append(TestResult(
                    test_name="test_suite",
                    passed=False,
                    output=output[:300],
                    error=output[:300],
                ))
            else:
                results.append(TestResult(
                    test_name="test_suite",
                    passed=True,
                    output=output[:300] if output else "No output",
                ))

        return results