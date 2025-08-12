#!/usr/bin/env python3

import argparse
import json
import sys
import os
import frida
from colorama import init, Fore, Back, Style
import traceback

init(autoreset=True)

class FridaUEExplorer:
    def __init__(self):
        self.session = None
        self.script = None
        self.config = None
        self.api = None

    def load_config(self, config_path):
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            print(f"[+] Config '{self.config['name']}' loaded.")
            return True
        except Exception as e:
            print(f"[-] Failed to load config: {e}")
            return False

    def attach_to_process(self, process_identifier, spawn=False, usb=False, remote=None):
        """Attach to target process"""
        try:
            if usb:
                device = frida.get_usb_device()
                print("[+] Connected to USB device")
            elif remote:
                device = frida.get_remote_device()
                print(f"[+] Connected to remote device")
            else:
                device = frida.get_local_device()
                print("[+] Connected to local device")

            if spawn:
                if usb:
                    pid = device.spawn([process_identifier])
                    print(f"[+] Spawned '{process_identifier}' (PID: {pid})")
                    session = device.attach(pid)
                    device.resume(pid)
                else:
                    print("[-] Spawn mode only supported for USB/mobile devices")
                    return False
            else:
                if isinstance(process_identifier, str) and not process_identifier.isdigit():
                    try:
                        process = device.get_process(process_identifier)
                        session = device.attach(process.pid)
                        print(f"[+] Attached to process '{process.name}' (PID: {process.pid})")
                    except frida.ProcessNotFoundError:
                        print(f"[-] Process '{process_identifier}' not found")
                        return False
                else:
                    pid = int(process_identifier)
                    session = device.attach(pid)
                    print(f"[+] Attached to process (PID: {pid})")

            self.session = session
            return True

        except Exception as e:
            print(f"[-] Failed to attach to process: {e}")
            return False

    def load_agent(self, agent_path="_agent.js"):
        """Load and initialize the Frida agent"""
        try:
            if not os.path.exists(agent_path):
                print(f"[-] Agent file '{agent_path}' not found")
                return False

            with open(agent_path, 'r', encoding='utf-8') as f:
                agent_code = f.read()

            script = self.session.create_script(agent_code)
            script.on('message', self._on_message)
            script.load()

            self.script = script
            self.api = script.exports

            if self.config:
                config_data = json.dumps(self.config)
                result = self.api.init(config_data)
                if result:
                    print("[+] Agent initialized successfully.")
                    return True
                else:
                    print("[-] Agent initialization failed.")
                    return False
            else:
                print("[-] No config loaded")
                return False

        except Exception as e:
            print(f"[-] Failed to load agent: {e}")
            traceback.print_exc()
            return False

    def _on_message(self, message, data):
        """Handle messages from the agent"""
        if message['type'] == 'send':
            payload = message.get('payload', '')
            if isinstance(payload, str):
                print(f"[Agent] {payload}")
            else:
                print(f"[Agent] {json.dumps(payload, indent=2)}")
        elif message['type'] == 'error':
            print(f"[Error] {message}")

    def cmd_info(self, args=None):
        """Display UE globals information"""
        try:
            result = self.api.info()
            if 'error' in result:
                print(f"[-] Error: {result['error']}")
                return

            print(f"\n{Fore.GREEN}=== UE Information ==={Style.RESET_ALL}")
            print(f"GObjects: {Fore.YELLOW}{result.get('GObjects', 'Unknown')}{Style.RESET_ALL}")
            print(f"GNames:   {Fore.YELLOW}{result.get('GNames', 'Unknown')}{Style.RESET_ALL}")
            print(f"GWorld:   {Fore.YELLOW}{result.get('GWorld', 'Unknown')}{Style.RESET_ALL}")
            print(f"Object Count: {Fore.CYAN}{result.get('ObjectCount', 0)}{Style.RESET_ALL}")

        except Exception as e:
            print(f"[-] Error getting info: {e}")

    def cmd_dump(self, args):
        """Dump object at specified address"""
        if not args:
            print("Usage: dump <address>")
            return

        address = args[0]
        try:
            result = self.api.dump(address)
            if 'error' in result:
                print(f"[-] Error: {result['error']}")
                return

            self._print_object(result)

        except Exception as e:
            print(f"[-] Error dumping object: {e}")

    def cmd_world(self, args=None):
        """Dump GWorld object"""
        try:
            result = self.api.world()
            if 'error' in result:
                print(f"[-] Error: {result['error']}")
                return

            print(f"\n{Fore.GREEN}=== GWorld ==={Style.RESET_ALL}")
            self._print_object(result)

        except Exception as e:
            print(f"[-] Error dumping world: {e}")

    def cmd_find(self, args):
        """Find objects by name"""
        if not args:
            print("Usage: find <object_name>")
            return

        name = ' '.join(args)
        try:
            results = self.api.find(name)
            
            if not results:
                print(f"[-] No objects found matching '{name}'")
                return

            print(f"\n{Fore.GREEN}=== Found {len(results)} object(s) matching '{name}' ==={Style.RESET_ALL}")
            for i, obj in enumerate(results):
                print(f"{Fore.CYAN}[{i+1}]{Style.RESET_ALL} {Fore.YELLOW}{obj['Name']}{Style.RESET_ALL} ({obj['Class']}) @ {obj['Address']}")

        except Exception as e:
            print(f"[-] Error finding objects: {e}")

    def cmd_findclass(self, args):
        """Find objects by class name"""
        if not args:
            print("Usage: findclass <class_name>")
            return

        class_name = ' '.join(args)
        try:
            results = self.api.findclass(class_name)
            
            if not results:
                print(f"[-] No objects found of class '{class_name}'")
                return

            print(f"\n{Fore.GREEN}=== Found {len(results)} object(s) of class '{class_name}' ==={Style.RESET_ALL}")
            for i, obj in enumerate(results):
                print(f"{Fore.CYAN}[{i+1}]{Style.RESET_ALL} {Fore.YELLOW}{obj['Name']}{Style.RESET_ALL} ({obj['Class']}) @ {obj['Address']}")

        except Exception as e:
            print(f"[-] Error finding objects by class: {e}")

    def cmd_player(self, args=None):
        """Find and dump PlayerController"""
        try:
            results = self.api.findclass("PlayerController")
            if not results:
                print("[-] No PlayerController found")
                return

            print(f"\n{Fore.GREEN}=== PlayerController ==={Style.RESET_ALL}")
            controller = results[0]
            print(f"Found: {controller['Name']} @ {controller['Address']}")
            
            result = self.api.dump(controller['Address'])
            if 'error' not in result:
                self._print_object(result)

        except Exception as e:
            print(f"[-] Error finding PlayerController: {e}")

    def cmd_pawn(self, args=None):
        """Find and dump Pawn"""
        try:
            results = self.api.findclass("Pawn")
            if not results:
                print("[-] No Pawn found")
                return

            print(f"\n{Fore.GREEN}=== Pawn ==={Style.RESET_ALL}")
            pawn = results[0]
            print(f"Found: {pawn['Name']} @ {pawn['Address']}")
            
            result = self.api.dump(pawn['Address'])
            if 'error' not in result:
                self._print_object(result)

        except Exception as e:
            print(f"[-] Error finding Pawn: {e}")

    def cmd_help(self, args=None):
        """Show help information"""
        print(f"\n{Fore.GREEN}=== frida-uexplorer Commands ==={Style.RESET_ALL}")
        print(f"{Fore.YELLOW}info{Style.RESET_ALL}           - Show UE globals information")
        print(f"{Fore.YELLOW}dump <addr>{Style.RESET_ALL}    - Dump object at address")
        print(f"{Fore.YELLOW}world{Style.RESET_ALL}          - Dump GWorld object")
        print(f"{Fore.YELLOW}find <name>{Style.RESET_ALL}    - Find objects by name")
        print(f"{Fore.YELLOW}findclass <cls>{Style.RESET_ALL} - Find objects by class name")
        print(f"{Fore.YELLOW}player{Style.RESET_ALL}         - Find and dump PlayerController")
        print(f"{Fore.YELLOW}pawn{Style.RESET_ALL}           - Find and dump Pawn")
        print(f"{Fore.YELLOW}help{Style.RESET_ALL}           - Show this help")
        print(f"{Fore.YELLOW}exit{Style.RESET_ALL}           - Exit the explorer")

    def _print_object(self, obj):
        """Pretty print object information"""
        if not obj:
            return

        print(f"Address: {Fore.YELLOW}{obj.get('Address', 'Unknown')}{Style.RESET_ALL}")
        print(f"Name:    {Fore.CYAN}{obj.get('Name', 'Unknown')}{Style.RESET_ALL}")
        print(f"Class:   {Fore.MAGENTA}{obj.get('Class', 'Unknown')}{Style.RESET_ALL}")
        
        if obj.get('Outer'):
            print(f"Outer:   {Fore.GREEN}{obj['Outer']}{Style.RESET_ALL}")

        properties = obj.get('Properties', [])
        if properties:
            print(f"\n{Fore.GREEN}Properties ({len(properties)}):{Style.RESET_ALL}")
            for prop in properties:
                print(f"  {Fore.YELLOW}{prop['Name']:20}{Style.RESET_ALL} {Fore.CYAN}{prop['Type']:15}{Style.RESET_ALL} @ 0x{prop['Offset']:04X}")

    def run_interactive(self):
        """Run interactive command loop"""
        print(f"\n{Fore.GREEN}frida-uexplorer interactive mode{Style.RESET_ALL}")
        print(f"Type '{Fore.YELLOW}help{Style.RESET_ALL}' for available commands")

        commands = {
            'info': self.cmd_info,
            'dump': self.cmd_dump,
            'world': self.cmd_world,
            'find': self.cmd_find,
            'findclass': self.cmd_findclass,
            'player': self.cmd_player,
            'pawn': self.cmd_pawn,
            'help': self.cmd_help,
        }

        while True:
            try:
                user_input = input(f"\n{Fore.GREEN}frida-uexplorer>{Style.RESET_ALL} ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ['exit', 'quit']:
                    break

                parts = user_input.split()
                command = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []

                if command in commands:
                    commands[command](args)
                else:
                    print(f"[-] Unknown command: {command}")
                    print(f"Type '{Fore.YELLOW}help{Style.RESET_ALL}' for available commands")

            except KeyboardInterrupt:
                print("\n[!] Interrupted by user")
                break
            except Exception as e:
                print(f"[-] Error: {e}")

        print("[+] Exiting...")
        if self.session:
            self.session.detach()

def main():
    parser = argparse.ArgumentParser(description='Frida UE Explorer - Interactive Unreal Engine memory exploration tool')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-n', '--name', type=str, help='Process name to attach to')
    group.add_argument('-p', '--pid', type=int, help='Process ID to attach to')
    group.add_argument('-f', '--spawn', type=str, help='Process to spawn (mobile)')
    
    parser.add_argument('-c', '--config', type=str, required=True, help='Configuration file path')
    parser.add_argument('-U', '--usb', action='store_true', help='Connect to USB device (mobile)')
    parser.add_argument('-H', '--host', type=str, help='Connect to remote frida-server')
    
    args = parser.parse_args()

    explorer = FridaUEExplorer()

    if not explorer.load_config(args.config):
        sys.exit(1)

    if args.spawn:
        if not explorer.attach_to_process(args.spawn, spawn=True, usb=args.usb):
            sys.exit(1)
    elif args.name:
        if not explorer.attach_to_process(args.name, usb=args.usb, remote=args.host):
            sys.exit(1)
    elif args.pid:
        if not explorer.attach_to_process(args.pid, usb=args.usb, remote=args.host):
            sys.exit(1)

    if not explorer.load_agent():
        sys.exit(1)

    explorer.run_interactive()

if __name__ == '__main__':
    main()