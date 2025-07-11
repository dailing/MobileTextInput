#!/usr/bin/env python3
"""
Instance Manager
Classes for managing multiple software application instances across different operating systems
"""

import logging
import platform
import subprocess
import os
import ctypes
from ctypes import wintypes
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Windows API constants and setup
CURRENT_OS = platform.system()
IS_WINDOWS = CURRENT_OS == "Windows"
IS_MACOS = CURRENT_OS == "Darwin"

# Windows-specific setup
if IS_WINDOWS:
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # Windows API constants
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010

        # Window show states
        SW_RESTORE = 9
        SW_SHOW = 5
        SW_SHOWMAXIMIZED = 3
        SW_SHOWMINIMIZED = 2
        SW_SHOWNA = 8
        SW_SHOWNOACTIVATE = 4
        SW_SHOWNORMAL = 1

        WINDOWS_API_AVAILABLE = True
        logger.info("✅ Windows API available for instance management")
    except ImportError:
        WINDOWS_API_AVAILABLE = False
        user32 = None
        kernel32 = None
        logger.warning("⚠️ Windows API not available")
else:
    WINDOWS_API_AVAILABLE = False
    user32 = None
    kernel32 = None


class ApplicationInstanceManager(ABC):
    """Abstract base class for managing software application instances"""

    @abstractmethod
    def list_instances(self) -> List[Dict[str, Any]]:
        """
        List all running instances of the target application

        Returns:
            List of dictionaries containing instance information:
            - id: Unique identifier for the instance
            - title: Window title
            - workspace: Workspace name extracted from title
            - Additional OS-specific fields
        """
        pass

    @abstractmethod
    def focus_instance(self, instance_id: str) -> bool:
        """
        Bring a specific application instance to the front and focus it

        Args:
            instance_id: The unique identifier of the instance to focus

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the instance manager is available on the current system

        Returns:
            bool: True if available, False otherwise
        """
        pass

    @abstractmethod
    def get_target_application_name(self) -> str:
        """
        Get the name of the target application

        Returns:
            str: Application name (e.g., "Cursor", "VSCode", etc.)
        """
        pass


class MacOSApplicationInstanceManager(ApplicationInstanceManager):
    """macOS implementation of application instance management using AppleScript"""

    def __init__(self, application_name: str = "Cursor"):
        self.application_name = application_name
        self.instances_cache = []

    def get_target_application_name(self) -> str:
        """Get the target application name"""
        return self.application_name

    def is_available(self) -> bool:
        """Check if macOS instance management is available"""
        return IS_MACOS

    def list_instances(self) -> List[Dict[str, Any]]:
        """List all application instances on macOS using AppleScript"""
        if not self.is_available():
            logger.error("❌ macOS instance manager not available")
            return []

        # First, test if we can access application windows
        count_script = f"""
        tell application "System Events"
            set appProcesses to every application process whose name is "{self.application_name}"
            set totalWindows to 0
            repeat with appProcess in appProcesses
                set windowList to every window of appProcess
                set totalWindows to totalWindows + (count of windowList)
            end repeat
            return totalWindows as string
        end tell
        """

        try:
            logger.info(f"🔍 Checking for {self.application_name} windows on macOS...")
            result = subprocess.run(
                ["osascript", "-e", count_script],
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip() == "0":
                logger.info(f"📋 No {self.application_name} windows found")
                return []

        except Exception as e:
            logger.error(f"❌ Failed to check {self.application_name} windows: {e}")
            return []

        # Get window names and details
        window_script = f"""
        tell application "System Events"
            set appProcesses to every application process whose name is "{self.application_name}"
            set windowNames to {{}}
            
            repeat with appProcess in appProcesses
                set windowList to every window of appProcess
                repeat with currentWindow in windowList
                    try
                        set windowName to name of currentWindow
                        if windowName is not "" then
                            set end of windowNames to windowName
                        end if
                    end try
                end repeat
            end repeat
            
            -- Convert list to string manually
            set resultString to ""
            repeat with i from 1 to count of windowNames
                set resultString to resultString & item i of windowNames
                if i < count of windowNames then
                    set resultString to resultString & "|"
                end if
            end repeat
            
            return resultString
        end tell
        """

        try:
            logger.info(f"🔍 Getting {self.application_name} window names...")
            result = subprocess.run(
                ["osascript", "-e", window_script],
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                window_names = result.stdout.strip().split("|")
                logger.info(
                    f"📋 Found {len(window_names)} {self.application_name} windows"
                )

                instances = []
                for i, window_name in enumerate(window_names):
                    if window_name.strip():
                        # Extract workspace name from window title
                        workspace_name = self._extract_workspace_name(window_name)

                        instance_info = {
                            "id": f"macos_{i}",
                            "title": window_name.strip(),
                            "workspace": workspace_name,
                            "platform": "macOS",
                            "application": self.application_name,
                        }
                        instances.append(instance_info)

                self.instances_cache = instances
                logger.info(
                    f"✅ Found {len(instances)} {self.application_name} instances on macOS"
                )
                return instances
            else:
                logger.info(f"📋 No {self.application_name} windows found")
                return []

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ AppleScript execution failed: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return []

    def focus_instance(self, instance_id: str) -> bool:
        """Focus a specific application instance on macOS"""
        if not self.is_available():
            logger.error("❌ macOS instance manager not available")
            return False

        # Find the instance in our cache
        target_instance = None
        for instance in self.instances_cache:
            if instance["id"] == instance_id:
                target_instance = instance
                break

        if not target_instance:
            logger.error(f"❌ Instance {instance_id} not found")
            return False

        title = target_instance["title"]
        workspace = target_instance["workspace"]

        logger.info(f"🎯 Focusing {self.application_name} instance: {workspace}")
        logger.info(f"   - Title: {title}")

        # Escape quotes in window title
        escaped_title = title.replace('"', '\\"')

        script = f"""
        tell application "System Events"
            tell application process "{self.application_name}"
                set frontmost to true
                try
                    -- Get window count first
                    set windowCount to count of windows
                    log "Total windows: " & windowCount
                    
                    -- Try to find and activate the window by name
                    set targetWindow to first window whose name is "{escaped_title}"
                    
                    -- Bring the target window to front
                    try
                        set index of targetWindow to 1
                        log "Method 1 (set index) succeeded"
                    on error
                        try
                            perform action "AXRaise" of targetWindow
                            log "Method 2 (AXRaise) succeeded"
                        on error
                            click targetWindow
                            log "Method 3 (click) succeeded"
                        end try
                    end try
                    
                    -- Verify the window is now frontmost
                    set frontWindow to window 1
                    set frontWindowName to name of frontWindow
                    log "Front window is now: " & frontWindowName
                    
                    return "success:" & frontWindowName
                on error errMsg
                    log "Error: " & errMsg
                    return "error:" & errMsg
                end try
            end tell
        end tell
        """

        try:
            logger.info("🍎 Executing AppleScript for window activation...")
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, check=True
            )

            output = result.stdout.strip()
            logger.info(f"🍎 AppleScript output: '{output}'")

            if "success:" in output:
                activated_window = output.split("success:")[1]
                logger.info(f"✅ Successfully focused window: '{activated_window}'")
                return True
            elif "error:" in output:
                error_msg = output.split("error:")[1]
                logger.error(f"❌ AppleScript error: {error_msg}")
                return self._fallback_focus(workspace)
            else:
                logger.error(f"❌ Unexpected AppleScript output: {output}")
                return False

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to execute AppleScript: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during window activation: {e}")
            return False

    def _extract_workspace_name(self, title: str) -> str:
        """Extract workspace name from window title"""
        # Format: "filename — workspace" or "filename - workspace"
        if " — " in title:  # Using em dash
            parts = title.split(" — ")
            if len(parts) >= 2:
                return parts[1].strip()
        elif " - " in title:  # Fallback for regular dash
            parts = title.split(" - ")
            if len(parts) >= 2:
                return parts[1].strip()
        return "Unknown"

    def _fallback_focus(self, workspace: str) -> bool:
        """Fallback approach to focus window by workspace"""
        logger.info("🔄 Trying fallback approach...")

        simple_script = f"""
        tell application "{self.application_name}"
            activate
            try
                set targetWindow to first window whose name contains "{workspace}"
                set index of targetWindow to 1
                return "fallback_success"
            on error
                return "app_activated"
            end try
        end tell
        """

        try:
            fallback_result = subprocess.run(
                ["osascript", "-e", simple_script],
                capture_output=True,
                text=True,
                check=True,
            )

            fallback_output = fallback_result.stdout.strip()
            logger.info(f"🔄 Fallback result: '{fallback_output}'")

            if "success" in fallback_output or "activated" in fallback_output:
                logger.info(f"✅ Fallback focus succeeded: {workspace}")
                return True
            return False

        except Exception as fallback_error:
            logger.error(f"❌ Fallback approach failed: {fallback_error}")
            return False


class WindowsApplicationInstanceManager(ApplicationInstanceManager):
    """Windows implementation of application instance management using Windows API"""

    def __init__(self, application_name: str = "Cursor"):
        self.application_name = application_name
        self.process_names = self._get_process_names()
        self.instances_cache = []

    def get_target_application_name(self) -> str:
        """Get the target application name"""
        return self.application_name

    def _get_process_names(self) -> List[str]:
        """Get possible process names for the application"""
        if self.application_name.lower() == "cursor":
            return [
                "cursor.exe",
                "cursor",
                "Cursor.exe",
                "Cursor",
                "cursor-ide.exe",
                "cursor-ide",
                "CursorIDE.exe",
                "CursorIDE",
            ]
        elif self.application_name.lower() in ["vscode", "code"]:
            return ["code.exe", "code", "Code.exe", "Code"]
        else:
            # Generic fallback
            app_lower = self.application_name.lower()
            app_title = self.application_name.title()
            return [
                f"{app_lower}.exe",
                app_lower,
                f"{app_title}.exe",
                app_title,
            ]

    def is_available(self) -> bool:
        """Check if Windows instance management is available"""
        return IS_WINDOWS and WINDOWS_API_AVAILABLE

    def list_instances(self) -> List[Dict[str, Any]]:
        """List all application instances on Windows using Windows API"""
        if not self.is_available():
            logger.error("❌ Windows instance manager not available")
            return []

        try:
            logger.info(
                f"🔍 Searching for {self.application_name} windows on Windows..."
            )
            logger.info(f"🔍 DEBUG: Looking for process names: {self.process_names}")

            # Use a simple list to collect matches - Windows API callbacks have restrictions
            found_matches = []
            all_windows_debug = []

            # Callback function to enumerate windows
            def enum_windows_callback(hwnd, windows):
                try:
                    if user32.IsWindowVisible(hwnd):
                        # Get window title
                        title_length = user32.GetWindowTextLengthW(hwnd)
                        if title_length > 0:
                            title_buffer = ctypes.create_unicode_buffer(
                                title_length + 1
                            )
                            user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
                            title = title_buffer.value

                            # Get process ID
                            process_id = wintypes.DWORD()
                            user32.GetWindowThreadProcessId(
                                hwnd, ctypes.byref(process_id)
                            )

                            # Get process name
                            try:
                                process_handle = kernel32.OpenProcess(
                                    PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                                    False,
                                    process_id.value,
                                )
                                if process_handle:
                                    process_name_buffer = ctypes.create_unicode_buffer(
                                        260
                                    )
                                    if kernel32.QueryFullProcessImageNameW(
                                        process_handle,
                                        0,
                                        process_name_buffer,
                                        ctypes.byref(wintypes.DWORD(260)),
                                    ):
                                        process_path = process_name_buffer.value
                                        process_name = os.path.basename(process_path)

                                        # Check if it matches our target application
                                        process_lower = process_name.lower()
                                        target_names_lower = [
                                            name.lower() for name in self.process_names
                                        ]

                                        # Add to debug list if relevant
                                        if any(
                                            keyword in title.lower()
                                            for keyword in [
                                                "cursor",
                                                "visual studio",
                                                "code",
                                                "editor",
                                            ]
                                        ) or any(
                                            keyword in process_name.lower()
                                            for keyword in ["cursor", "code", "editor"]
                                        ):
                                            all_windows_debug.append(
                                                {
                                                    "title": title,
                                                    "process_name": process_name,
                                                    "process_path": process_path,
                                                    "matches_target": process_lower
                                                    in target_names_lower,
                                                }
                                            )

                                        # If it matches, add to found_matches
                                        if process_lower in target_names_lower:
                                            window_info = {
                                                "hwnd": hwnd,
                                                "title": title,
                                                "process_id": process_id.value,
                                                "process_name": process_name,
                                            }
                                            found_matches.append(window_info)

                                    kernel32.CloseHandle(process_handle)
                            except Exception as e:
                                pass  # Silently skip errors in callback

                except Exception as callback_error:
                    pass  # Silently skip callback errors

                return True

            # Define callback function type
            WNDENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_bool, wintypes.HWND, ctypes.POINTER(ctypes.py_object)
            )

            # Enumerate all windows
            logger.info("🔍 DEBUG: Starting window enumeration...")
            enum_callback = WNDENUMPROC(enum_windows_callback)
            user32.EnumWindows(
                enum_callback, ctypes.py_object(None)
            )  # We don't use the callback parameter

            # Now process the matches found outside the callback
            logger.info(
                f"🔍 DEBUG: After enumeration, found {len(found_matches)} matches"
            )
            for match in found_matches:
                logger.info(
                    f"🎯 MATCH FOUND: {match['process_name']} - {match['title']}"
                )

            windows = found_matches

            # Debug output: Show what we found
            logger.info(
                f"🔍 DEBUG: Found {len(all_windows_debug)} potentially relevant windows:"
            )
            for debug_window in all_windows_debug[
                :10
            ]:  # Limit to first 10 to avoid spam
                logger.info(f"   - Title: {debug_window['title']}")
                logger.info(f"     Process: {debug_window['process_name']}")
                logger.info(f"     Path: {debug_window['process_path']}")
                logger.info(f"     Matches Target: {debug_window['matches_target']}")
                logger.info("   ---")

            if len(all_windows_debug) > 10:
                logger.info(f"   ... and {len(all_windows_debug) - 10} more")

            # Process found windows
            instances = []
            for i, window in enumerate(windows):
                title = window["title"]
                workspace_name = self._extract_workspace_name(title)

                instance_info = {
                    "id": f"windows_{i}",
                    "title": title,
                    "workspace": workspace_name,
                    "platform": "Windows",
                    "application": self.application_name,
                    "hwnd": window["hwnd"],
                    "process_id": window["process_id"],
                }
                instances.append(instance_info)

            self.instances_cache = instances
            logger.info(
                f"✅ Found {len(instances)} {self.application_name} instances on Windows"
            )
            return instances

        except Exception as e:
            logger.error(f"❌ Error enumerating Windows: {e}")
            return []

    def focus_instance(self, instance_id: str) -> bool:
        """Focus a specific application instance on Windows"""
        if not self.is_available():
            logger.error("❌ Windows instance manager not available")
            return False

        # Find the instance in our cache
        target_instance = None
        for instance in self.instances_cache:
            if instance["id"] == instance_id:
                target_instance = instance
                break

        if not target_instance:
            logger.error(f"❌ Instance {instance_id} not found")
            return False

        hwnd = target_instance["hwnd"]
        workspace = target_instance["workspace"]
        title = target_instance["title"]

        logger.info(
            f"🎯 Focusing {self.application_name} instance on Windows: {workspace}"
        )
        logger.info(f"   - HWND: {hwnd}")
        logger.info(f"   - Title: {title}")

        try:
            # Check if window is minimized
            if user32.IsIconic(hwnd):
                logger.info("🔄 Window is minimized, restoring...")
                user32.ShowWindow(hwnd, SW_RESTORE)

            # Bring window to foreground
            logger.info("🔄 Bringing window to foreground...")
            user32.SetForegroundWindow(hwnd)

            # Additional method to ensure window is activated
            user32.BringWindowToTop(hwnd)

            # Check if successful
            foreground_hwnd = user32.GetForegroundWindow()
            if foreground_hwnd == hwnd:
                logger.info(f"✅ Successfully focused window: {title}")
                return True
            else:
                logger.info("✅ Window focus completed (may take effect shortly)")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to focus window: {e}")
            return False

    def _extract_workspace_name(self, title: str) -> str:
        """Extract workspace name from window title"""
        # Format: "filename — workspace" or "filename - workspace"
        if " — " in title:  # Using em dash
            parts = title.split(" — ")
            if len(parts) >= 2:
                return parts[1].strip()
        elif " - " in title:  # Fallback for regular dash
            parts = title.split(" - ")
            if len(parts) >= 2:
                return parts[1].strip()
        return "Unknown"


class LinuxApplicationInstanceManager(ApplicationInstanceManager):
    """Linux implementation placeholder - not implemented yet"""

    def __init__(self, application_name: str = "Cursor"):
        self.application_name = application_name

    def get_target_application_name(self) -> str:
        """Get the target application name"""
        return self.application_name

    def is_available(self) -> bool:
        """Linux implementation not available yet"""
        return False

    def list_instances(self) -> List[Dict[str, Any]]:
        """Linux implementation not available yet"""
        logger.warning(
            f"⚠️ Linux {self.application_name} instance management not implemented yet"
        )
        return []

    def focus_instance(self, instance_id: str) -> bool:
        """Linux implementation not available yet"""
        logger.warning(
            f"⚠️ Linux {self.application_name} instance management not implemented yet"
        )
        return False


def create_application_instance_manager(
    application_name: str = "Cursor",
) -> ApplicationInstanceManager:
    """
    Factory function to create the appropriate application instance manager
    based on the current operating system

    Args:
        application_name: Name of the application to manage (e.g., "Cursor", "VSCode")

    Returns:
        ApplicationInstanceManager: The appropriate instance manager for the current OS
    """
    current_os = platform.system()

    if current_os == "Darwin":  # macOS
        logger.info(f"🍎 Creating macOS {application_name} instance manager")
        return MacOSApplicationInstanceManager(application_name)
    elif current_os == "Windows":
        logger.info(f"🪟 Creating Windows {application_name} instance manager")
        return WindowsApplicationInstanceManager(application_name)
    elif current_os == "Linux":
        logger.info(
            f"🐧 Creating Linux {application_name} instance manager (placeholder)"
        )
        return LinuxApplicationInstanceManager(application_name)
    else:
        logger.warning(f"⚠️ Unsupported OS: {current_os}")
        return LinuxApplicationInstanceManager(
            application_name
        )  # Use placeholder for unsupported OS


# Export the main classes and factory function
__all__ = [
    "ApplicationInstanceManager",
    "MacOSApplicationInstanceManager",
    "WindowsApplicationInstanceManager",
    "LinuxApplicationInstanceManager",
    "create_application_instance_manager",
]
