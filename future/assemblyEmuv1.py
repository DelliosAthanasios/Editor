#!/usr/bin/env python3
"""
Unicorn-Enhanced Assembly Simulator
A realistic assembly simulator using Unicorn Engine for accurate CPU emulation.

Installation required:
pip install unicorn-engine keystone-engine capstone
"""

import sys
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

try:
    import unicorn as uc
    from unicorn import x86_const, arm64_const, arm_const, mips_const
    UNICORN_AVAILABLE = True
except ImportError:
    UNICORN_AVAILABLE = False
    print("Warning: Unicorn Engine not available. Install with: pip install unicorn-engine")

try:
    import keystone as ks
    KEYSTONE_AVAILABLE = True
except ImportError:
    KEYSTONE_AVAILABLE = False
    print("Warning: Keystone assembler not available. Install with: pip install keystone-engine")

try:
    import capstone as cs
    CAPSTONE_AVAILABLE = True
except ImportError:
    CAPSTONE_AVAILABLE = False
    print("Warning: Capstone disassembler not available. Install with: pip install capstone")

class UnicornArchitecture(Enum):
    X86_64 = ("x86-64", uc.UC_ARCH_X86, uc.UC_MODE_64, ks.KS_ARCH_X86, ks.KS_MODE_64, cs.CS_ARCH_X86, cs.CS_MODE_64)
    X86_32 = ("x86-32", uc.UC_ARCH_X86, uc.UC_MODE_32, ks.KS_ARCH_X86, ks.KS_MODE_32, cs.CS_ARCH_X86, cs.CS_MODE_32)
    ARM64 = ("AArch64", uc.UC_ARCH_ARM64, uc.UC_MODE_ARM, ks.KS_ARCH_ARM64, ks.KS_MODE_LITTLE_ENDIAN, cs.CS_ARCH_ARM64, cs.CS_MODE_ARM)
    ARM32 = ("ARM", uc.UC_ARCH_ARM, uc.UC_MODE_ARM, ks.KS_ARCH_ARM, ks.KS_MODE_ARM, cs.CS_ARCH_ARM, cs.CS_MODE_ARM)
    MIPS32 = ("MIPS", uc.UC_ARCH_MIPS, uc.UC_MODE_MIPS32, ks.KS_ARCH_MIPS, ks.KS_MODE_MIPS32, cs.CS_ARCH_MIPS, cs.CS_MODE_MIPS32)
    MIPS64 = ("MIPS64", uc.UC_ARCH_MIPS, uc.UC_MODE_MIPS64, ks.KS_ARCH_MIPS, ks.KS_MODE_MIPS64, cs.CS_ARCH_MIPS, cs.CS_MODE_MIPS64)

@dataclass
class EmulationResult:
    """Result of assembly code emulation"""
    success: bool
    registers_before: Dict[str, int] = field(default_factory=dict)
    registers_after: Dict[str, int] = field(default_factory=dict)
    memory_changes: List[Tuple[int, bytes, bytes]] = field(default_factory=list)  # (address, before, after)
    disassembly: List[str] = field(default_factory=list)
    error_message: str = ""
    instructions_executed: int = 0
    machine_code: bytes = b""
    execution_time_ns: int = 0

class UnicornEmulator:
    """Unicorn Engine-based CPU emulator"""
    
    def __init__(self, architecture: UnicornArchitecture):
        if not UNICORN_AVAILABLE:
            raise ImportError("Unicorn Engine not available")
        
        self.architecture = architecture
        self.name, self.uc_arch, self.uc_mode, self.ks_arch, self.ks_mode, self.cs_arch, self.cs_mode = architecture.value
        
        # Initialize emulator
        self.uc = uc.Uc(self.uc_arch, self.uc_mode)
        
        # Memory layout (fixed non-overlapping addresses)
        self.MEMORY_SIZE = 2 * 1024 * 1024  # 2MB
        self.PAGE_SIZE = 4 * 1024  # 4KB
        
        # Align addresses to 4KB boundaries
        self.CODE_ADDRESS = 0x1000
        self.STACK_ADDRESS = self.CODE_ADDRESS + self.MEMORY_SIZE
        self.HEAP_ADDRESS = self.STACK_ADDRESS + self.MEMORY_SIZE
        
        # Map memory regions
        self.uc.mem_map(self.CODE_ADDRESS, self.MEMORY_SIZE)
        self.uc.mem_map(self.STACK_ADDRESS, self.MEMORY_SIZE)
        self.uc.mem_map(self.HEAP_ADDRESS, self.MEMORY_SIZE)
        
        # Initialize stack pointer based on architecture
        self._init_stack_pointer()
        
        # Initialize assembler and disassembler
        if KEYSTONE_AVAILABLE:
            self.assembler = ks.Ks(self.ks_arch, self.ks_mode)
        else:
            self.assembler = None
            
        if CAPSTONE_AVAILABLE:
            self.disassembler = cs.Cs(self.cs_arch, self.cs_mode)
        else:
            self.disassembler = None
    
    def _init_stack_pointer(self):
        """Initialize stack pointer based on architecture"""
        stack_top = self.STACK_ADDRESS + self.MEMORY_SIZE - 8
        
        if self.architecture == UnicornArchitecture.X86_64:
            self.uc.reg_write(x86_const.UC_X86_REG_RSP, stack_top)
        elif self.architecture == UnicornArchitecture.X86_32:
            self.uc.reg_write(x86_const.UC_X86_REG_ESP, stack_top)
        elif self.architecture == UnicornArchitecture.ARM64:
            self.uc.reg_write(arm64_const.UC_ARM64_REG_SP, stack_top)
        elif self.architecture == UnicornArchitecture.ARM32:
            self.uc.reg_write(arm_const.UC_ARM_REG_SP, stack_top)
        elif self.architecture in [UnicornArchitecture.MIPS32, UnicornArchitecture.MIPS64]:
            self.uc.reg_write(mips_const.UC_MIPS_REG_SP, stack_top)
    
    def assemble(self, assembly_code: str) -> Tuple[bytes, int]:
        """Assemble assembly code to machine code"""
        if not self.assembler:
            raise RuntimeError("Keystone assembler not available")
        
        try:
            # Clean up the assembly code
            lines = []
            for line in assembly_code.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith(';') and not line.startswith('//'):
                    # Remove comments
                    if ';' in line:
                        line = line.split(';')[0].strip()
                    if '//' in line:
                        line = line.split('//')[0].strip()
                    if line:
                        lines.append(line)
            
            clean_code = '\n'.join(lines)
            encoding, count = self.assembler.asm(clean_code)
            return bytes(encoding), count
        except Exception as e:
            raise RuntimeError(f"Assembly failed: {str(e)}")
    
    def disassemble(self, machine_code: bytes, address: int = 0) -> List[str]:
        """Disassemble machine code to assembly"""
        if not self.disassembler:
            return [f"Machine code: {machine_code.hex()}"]
        
        try:
            instructions = []
            for insn in self.disassembler.disasm(machine_code, address):
                instructions.append(f"{insn.address:08x}: {insn.mnemonic} {insn.op_str}")
            return instructions
        except Exception as e:
            return [f"Disassembly failed: {str(e)}"]
    
    def get_registers(self) -> Dict[str, int]:
        """Get current register values"""
        registers = {}
        
        if self.architecture == UnicornArchitecture.X86_64:
            reg_map = {
                'rax': x86_const.UC_X86_REG_RAX, 'rbx': x86_const.UC_X86_REG_RBX,
                'rcx': x86_const.UC_X86_REG_RCX, 'rdx': x86_const.UC_X86_REG_RDX,
                'rsi': x86_const.UC_X86_REG_RSI, 'rdi': x86_const.UC_X86_REG_RDI,
                'rbp': x86_const.UC_X86_REG_RBP, 'rsp': x86_const.UC_X86_REG_RSP,
                'r8': x86_const.UC_X86_REG_R8, 'r9': x86_const.UC_X86_REG_R9,
                'r10': x86_const.UC_X86_REG_R10, 'r11': x86_const.UC_X86_REG_R11,
                'r12': x86_const.UC_X86_REG_R12, 'r13': x86_const.UC_X86_REG_R13,
                'r14': x86_const.UC_X86_REG_R14, 'r15': x86_const.UC_X86_REG_R15,
                'rip': x86_const.UC_X86_REG_RIP, 'eflags': x86_const.UC_X86_REG_EFLAGS
            }
        elif self.architecture == UnicornArchitecture.X86_32:
            reg_map = {
                'eax': x86_const.UC_X86_REG_EAX, 'ebx': x86_const.UC_X86_REG_EBX,
                'ecx': x86_const.UC_X86_REG_ECX, 'edx': x86_const.UC_X86_REG_EDX,
                'esi': x86_const.UC_X86_REG_ESI, 'edi': x86_const.UC_X86_REG_EDI,
                'ebp': x86_const.UC_X86_REG_EBP, 'esp': x86_const.UC_X86_REG_ESP,
                'eip': x86_const.UC_X86_REG_EIP, 'eflags': x86_const.UC_X86_REG_EFLAGS
            }
        elif self.architecture == UnicornArchitecture.ARM64:
            reg_map = {f'x{i}': getattr(arm64_const, f'UC_ARM64_REG_X{i}') for i in range(31)}
            reg_map.update({
                'sp': arm64_const.UC_ARM64_REG_SP,
                'pc': arm64_const.UC_ARM64_REG_PC,
                'nzcv': arm64_const.UC_ARM64_REG_NZCV
            })
        elif self.architecture == UnicornArchitecture.ARM32:
            reg_map = {f'r{i}': getattr(arm_const, f'UC_ARM_REG_R{i}') for i in range(13)}
            reg_map.update({
                'sp': arm_const.UC_ARM_REG_SP,
                'lr': arm_const.UC_ARM_REG_LR,
                'pc': arm_const.UC_ARM_REG_PC,
                'cpsr': arm_const.UC_ARM_REG_CPSR
            })
        elif self.architecture in [UnicornArchitecture.MIPS32, UnicornArchitecture.MIPS64]:
            reg_map = {f'${i}': getattr(mips_const, f'UC_MIPS_REG_{i}') for i in range(32)}
            reg_map.update({
                'pc': mips_const.UC_MIPS_REG_PC,
                'hi': mips_const.UC_MIPS_REG_HI,
                'lo': mips_const.UC_MIPS_REG_LO
            })
        else:
            reg_map = {}
        
        for name, reg_id in reg_map.items():
            try:
                registers[name] = self.uc.reg_read(reg_id)
            except Exception:
                registers[name] = 0
        
        return registers
    
    def execute_assembly(self, assembly_code: str) -> EmulationResult:
        """Execute assembly code and return detailed results"""
        result = EmulationResult(success=False)
        
        try:
            # Get initial register state
            result.registers_before = self.get_registers()
            
            # Assemble the code
            machine_code, instruction_count = self.assemble(assembly_code)
            result.machine_code = machine_code
            result.instructions_executed = instruction_count
            
            # Disassemble for display
            result.disassembly = self.disassemble(machine_code, self.CODE_ADDRESS)
            
            # Write machine code to memory
            self.uc.mem_write(self.CODE_ADDRESS, machine_code)
            
            # Execute the code
            import time
            start_time = time.time_ns()
            self.uc.emu_start(self.CODE_ADDRESS, self.CODE_ADDRESS + len(machine_code))
            end_time = time.time_ns()
            
            result.execution_time_ns = end_time - start_time
            result.success = True
            
        except Exception as e:
            result.error_message = str(e)
        
        # Get final register state
        result.registers_after = self.get_registers()
        
        return result
    
    def reset(self):
        """Reset the emulator state"""
        # Re-initialize the emulator
        self.uc.close()
        self.uc = uc.Uc(self.uc_arch, self.uc_mode)
        
        # Re-map memory
        self.uc.mem_map(self.CODE_ADDRESS, self.MEMORY_SIZE)
        self.uc.mem_map(self.STACK_ADDRESS, self.MEMORY_SIZE)
        self.uc.mem_map(self.HEAP_ADDRESS, self.MEMORY_SIZE)
        
        # Re-initialize stack pointer
        self._init_stack_pointer()

class EnhancedAssemblySimulator:
    """Enhanced assembly simulator using Unicorn Engine"""
    
    def __init__(self):
        self.current_emulator = None
        self.current_architecture = None
        self.available_architectures = [arch for arch in UnicornArchitecture]
    
    def list_architectures(self) -> List[str]:
        """List all supported architectures"""
        return [arch.value[0] for arch in self.available_architectures]
    
    def select_architecture(self, architecture_name: str) -> bool:
        """Select an architecture by name"""
        if not UNICORN_AVAILABLE:
            print("Error: Unicorn Engine not available. Please install with: pip install unicorn-engine")
            return False
        
        try:
            for arch in self.available_architectures:
                if arch.value[0].lower() == architecture_name.lower():
                    self.current_architecture = arch
                    self.current_emulator = UnicornEmulator(arch)
                    return True
            return False
        except Exception as e:
            print(f"Error initializing architecture: {e}")
            return False
    
    def execute_assembly(self, assembly_code: str) -> EmulationResult:
        """Execute assembly code"""
        if not self.current_emulator:
            result = EmulationResult(success=False)
            result.error_message = "No architecture selected"
            return result
        
        return self.current_emulator.execute_assembly(assembly_code)
    
    def reset_emulator(self):
        """Reset the current emulator"""
        if self.current_emulator:
            self.current_emulator.reset()
    
    def get_current_registers(self) -> Dict[str, int]:
        """Get current register values"""
        if self.current_emulator:
            return self.current_emulator.get_registers()
        return {}

def print_register_changes(before: Dict[str, int], after: Dict[str, int]):
    """Print register changes in a formatted way"""
    print("\nRegister Changes:")
    print("=" * 50)
    
    changes = []
    for reg in set(before.keys()) | set(after.keys()):
        before_val = before.get(reg, 0)
        after_val = after.get(reg, 0)
        if before_val != after_val:
            changes.append((reg, before_val, after_val))
    
    if not changes:
        print("  No register changes")
        return
    
    for reg, before_val, after_val in sorted(changes):
        print(f"  {reg:6s}: 0x{before_val:016x} -> 0x{after_val:016x}")

def main():
    """Main function with enhanced CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Unicorn-Enhanced Assembly Simulator')
    parser.add_argument('--arch', help='Architecture to use')
    parser.add_argument('--code', help='Assembly code to execute')
    parser.add_argument('--file', help='File containing assembly code')
    parser.add_argument('--list', action='store_true', help='List supported architectures')
    parser.add_argument('--check', action='store_true', help='Check if dependencies are installed')
    
    args = parser.parse_args()
    
    if args.check:
        print("Dependency Check:")
        print(f"  Unicorn Engine: {'✓ Available' if UNICORN_AVAILABLE else '✗ Missing'}")
        print(f"  Keystone Assembler: {'✓ Available' if KEYSTONE_AVAILABLE else '✗ Missing'}")
        print(f"  Capstone Disassembler: {'✓ Available' if CAPSTONE_AVAILABLE else '✗ Missing'}")
        
        if not UNICORN_AVAILABLE:
            print("\nTo install missing dependencies:")
            print("  pip install unicorn-engine keystone-engine capstone")
        return
    
    if not UNICORN_AVAILABLE:
        print("Error: Unicorn Engine not available. Please install with:")
        print("  pip install unicorn-engine keystone-engine capstone")
        return
    
    simulator = EnhancedAssemblySimulator()
    
    if args.list:
        print("Supported Architectures:")
        for arch in simulator.list_architectures():
            print(f"  {arch}")
        return
    
    # Interactive mode
    if not args.arch and not args.code and not args.file:
        print("Unicorn-Enhanced Assembly Simulator")
        print("===================================")
        print("Powered by Unicorn Engine - Real CPU Emulation")
        
        while True:
            print("\nSupported Architectures:")
            architectures = simulator.list_architectures()
            for i, arch in enumerate(architectures, 1):
                print(f"{i:2d}. {arch}")
            
            try:
                choice = input("\nSelect architecture (number or name, 'q' to quit): ").strip()
                if choice.lower() == 'q':
                    break
                
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(architectures):
                        arch_name = architectures[idx]
                    else:
                        print("Invalid selection")
                        continue
                else:
                    arch_name = choice
                
                if simulator.select_architecture(arch_name):
                    print(f"\nSelected architecture: {arch_name}")
                    print("Real CPU emulation active!")
                    
                    # Show initial register state
                    registers = simulator.get_current_registers()
                    print(f"\nInitial Register State ({len(registers)} registers):")
                    for i, (reg, val) in enumerate(sorted(registers.items())):
                        if i < 8:  # Show first 8 registers
                            print(f"  {reg:6s}: 0x{val:016x}")
                        elif i == 8:
                            print(f"  ... and {len(registers) - 8} more registers")
                            break
                    
                    while True:
                        print("\nEnter assembly code (type 'END' to finish, 'RESET' to reset, 'BACK' to change arch):")
                        code_lines = []
                        while True:
                            line = input()
                            if line.strip().upper() == 'END':
                                break
                            elif line.strip().upper() == 'RESET':
                                simulator.reset_emulator()
                                print("Emulator state reset")
                                code_lines = []
                                break
                            elif line.strip().upper() == 'BACK':
                                code_lines = None
                                break
                            else:
                                code_lines.append(line)
                        
                        if code_lines is None:
                            break
                        
                        if code_lines:
                            code = '\n'.join(code_lines)
                            result = simulator.execute_assembly(code)
                            
                            if result.success:
                                print(f"\n✓ Execution successful!")
                                print(f"  Instructions executed: {result.instructions_executed}")
                                print(f"  Execution time: {result.execution_time_ns/1000:.2f} μs")
                                print(f"  Machine code: {result.machine_code.hex()}")
                                
                                if result.disassembly:
                                    print("\nDisassembly:")
                                    for line in result.disassembly[:5]:  # Show first 5 instructions
                                        print(f"  {line}")
                                    if len(result.disassembly) > 5:
                                        print(f"  ... and {len(result.disassembly) - 5} more instructions")
                                
                                print_register_changes(result.registers_before, result.registers_after)
                            else:
                                print(f"\n✗ Execution failed: {result.error_message}")
                else:
                    print(f"Unknown architecture: {arch_name}")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    else:
        # Command line mode
        if args.arch:
            if not simulator.select_architecture(args.arch):
                print(f"Unknown architecture: {args.arch}")
                return
        
        code = ""
        if args.code:
            code = args.code
        elif args.file:
            try:
                with open(args.file, 'r') as f:
                    code = f.read()
            except Exception as e:
                print(f"Error reading file: {e}")
                return
        
        if code and simulator.current_emulator:
            result = simulator.execute_assembly(code)
            
            if result.success:
                print(f"✓ Execution successful!")
                print(f"Machine code: {result.machine_code.hex()}")
                print_register_changes(result.registers_before, result.registers_after)
            else:
                print(f"✗ Execution failed: {result.error_message}")

if __name__ == "__main__":
    main()