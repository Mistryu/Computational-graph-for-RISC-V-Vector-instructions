"""
RISC-V Vector Extension (RVV) Instruction Disassembler

This module provides functionality to disassemble RISC-V Vector Extension
instructions into human-readable format.

Be warned, this is a work in progress and may not be 100% accurate.

CONFLICTING INSTRUCTIONS (same funct6, resolved by category/priority):

1. REDUCTION vs ARITHMETIC (funct6=0b000000, 0b000010, 0b000011, 0b000100, 0b000101, 0b000110, 0b000111):
    (funct6)  (reduction) (arithmetic)
   - 0b000000: vredsum vs vadd
   - 0b000010: vredor vs vsub
   - 0b000011: vredxor vs vrsub
   - 0b000100: vredminu vs vminu
   - 0b000101: vredmin vs vmin
   - 0b000110: vredmaxu vs vmaxu
   - 0b000111: vredmax vs vmax
   Resolution: Arithmetic checked first, reduction as fallback

2. SHIFT vs COMPARE (funct6=0b011000, 0b011001):
   (funct6)  (shift) (compare)
   - 0b011000: vsrl vs vmseq
   - 0b011001: vsra vs vmsne
   Resolution: Shift checked first, compare as fallback

3. MULTIPLY vs ARITHMETIC (funct6=0b100000, 0b100001, 0b100010, 0b100011, 0b100100, 0b100101, 0b100110, 0b100111):
   (funct6)  (multiply) (arithmetic)
   - 0b100000: vmul vs vsaddu
   - 0b100001: vmulh vs vsadd
   - 0b100010: vmulhsu vs vssubu
   - 0b100011: vmulhu vs vssub
   - 0b100100: vmadd vs vaaddu
   - 0b100101: vnmsub vs vaadd
   - 0b100110: vmacc vs vasubu
   - 0b100111: vnmsac vs vasub
   
   Resolution: Multiply checked first, arithmetic as fallback

4. WIDENING MULTIPLY vs SCALING SHIFT (funct6=0b101010, 0b101100):
   (funct6)  (widening multiply) (scaling shift)
   - 0b101010: vwmulsu vs vssrl
   - 0b101100: vwmacc vs vnclipu
   Resolution: Widening multiply checked first, scaling shift as fallback


If a better way to resolve conflicts is found, please update the code accordingly.
This works for me so I will keep it this way but updates are welcome :)
"""

from typing import Optional, Tuple


def extract_fields(instruction: int) -> Tuple[int, int, int, int, int, int, int, int]:
    """
    Extract all relevant fields from a 32-bit instruction.

    Returns a tuple of (opcode, funct6, vm, vs2, vs1_rs1, funct3, vd_rd, imm5)
    """
    opcode = instruction & 0x7F          # bits [6:0]
    funct6 = (instruction >> 26) & 0x3F  # bits [31:26]
    vm = (instruction >> 25) & 0x1       # bit [25]
    vs2 = (instruction >> 20) & 0x1F     # bits [24:20]
    vs1_rs1 = (instruction >> 15) & 0x1F # bits [19:15]
    funct3 = (instruction >> 12) & 0x7   # bits [14:12]
    vd_rd = (instruction >> 7) & 0x1F    # bits [11:7]
    imm5 = vs1_rs1                       # bits [19:15] when used as immediate
    
    return opcode, funct6, vm, vs2, vs1_rs1, funct3, vd_rd, imm5


def get_operand_category(funct3: int) -> Optional[str]:
    """
    Determine operand category from funct3 field.
    
    Returns the operand category string or None if invalid
    """
    category_map = {
        0b000: 'OPIVV',  # Vector-Vector Integer
        0b001: 'OPFVV',  # Vector-Vector Floating-Point
        0b010: 'OPMVV',  # Vector-Vector Mask
        0b011: 'OPIVI',  # Vector-Immediate Integer
        0b100: 'OPIVX',  # Vector-Scalar Integer
        0b101: 'OPFVF',  # Vector-Scalar Floating-Point
        0b110: 'OPMVX',  # Vector-Scalar Mask
        0b111: 'OPCFG',  # Configuration
    }
    return category_map.get(funct3)


def get_integer_arithmetic_mnemonic(funct6: int, category: str) -> Optional[str]:
    """
    Get mnemonic for integer arithmetic instructions.

    Returns the instruction mnemonic or None if not found
    """
    # Integer arithmetic opcode table (from RISC-V V spec 1.0)
    opcode_map = {
        # OPIVV
        ('OPIVV', 0b000000): 'vadd',
        ('OPIVV', 0b000010): 'vsub',
        ('OPIVV', 0b000011): 'vrsub',
        ('OPIVV', 0b000100): 'vminu',
        ('OPIVV', 0b000101): 'vmin',
        ('OPIVV', 0b000110): 'vmaxu',
        ('OPIVV', 0b000111): 'vmax',
        ('OPIVV', 0b001001): 'vand',
        ('OPIVV', 0b001010): 'vor',
        ('OPIVV', 0b001011): 'vxor',
        ('OPIVV', 0b001100): 'vrgather',
        ('OPIVV', 0b001110): 'vslideup',
        ('OPIVV', 0b001111): 'vslidedown',
        ('OPIVV', 0b010000): 'vadc',
        ('OPIVV', 0b010001): 'vmadc',
        ('OPIVV', 0b010010): 'vsbc',
        ('OPIVV', 0b010011): 'vmsbc',
        ('OPIVV', 0b010111): 'vmerge',
        ('OPIVV', 0b011000): 'vmseq',
        ('OPIVV', 0b011001): 'vmsne',
        ('OPIVV', 0b011010): 'vmsltu',
        ('OPIVV', 0b011011): 'vmslt',
        ('OPIVV', 0b011100): 'vmsleu',
        ('OPIVV', 0b011101): 'vmsle',
        ('OPIVV', 0b100000): 'vsaddu',
        ('OPIVV', 0b100001): 'vsadd',
        ('OPIVV', 0b100010): 'vssubu',
        ('OPIVV', 0b100011): 'vssub',
        ('OPIVV', 0b101000): 'vaaddu',
        ('OPIVV', 0b101010): 'vasub',
        ('OPIVV', 0b101100): 'vsmul',
        ('OPIVV', 0b110000): 'vwaddu',
        ('OPIVV', 0b110001): 'vwadd',
        ('OPIVV', 0b110010): 'vwsubu',
        ('OPIVV', 0b110011): 'vwsub',
        ('OPIVV', 0b110100): 'vwaddu.w',
        ('OPIVV', 0b110101): 'vwadd.w',
        ('OPIVV', 0b110110): 'vwsubu.w',
        ('OPIVV', 0b110111): 'vwsub.w',
        
        # OPIVX
        ('OPIVX', 0b000000): 'vadd',
        ('OPIVX', 0b000010): 'vsub',
        ('OPIVX', 0b000011): 'vrsub',
        ('OPIVX', 0b000100): 'vminu',
        ('OPIVX', 0b000101): 'vmin',
        ('OPIVX', 0b000110): 'vmaxu',
        ('OPIVX', 0b000111): 'vmax',
        ('OPIVX', 0b001001): 'vand',
        ('OPIVX', 0b001010): 'vor',
        ('OPIVX', 0b001011): 'vxor',
        ('OPIVX', 0b001100): 'vrgather',
        ('OPIVX', 0b001110): 'vslideup',
        ('OPIVX', 0b001111): 'vslidedown',
        ('OPIVX', 0b010000): 'vadc',
        ('OPIVX', 0b010001): 'vmadc',
        ('OPIVX', 0b010010): 'vsbc',
        ('OPIVX', 0b010011): 'vmsbc',
        ('OPIVX', 0b010111): 'vmerge',
        ('OPIVX', 0b011000): 'vmseq',
        ('OPIVX', 0b011001): 'vmsne',
        ('OPIVX', 0b011010): 'vmsltu',
        ('OPIVX', 0b011011): 'vmslt',
        ('OPIVX', 0b011100): 'vmsleu',
        ('OPIVX', 0b011101): 'vmsle',
        ('OPIVX', 0b011110): 'vmsgtu',
        ('OPIVX', 0b011111): 'vmsgt',
        ('OPIVX', 0b100000): 'vsaddu',
        ('OPIVX', 0b100001): 'vsadd',
        ('OPIVX', 0b100010): 'vssubu',
        ('OPIVX', 0b100011): 'vssub',
        ('OPIVX', 0b101000): 'vaaddu',
        ('OPIVX', 0b101010): 'vasubu',
        ('OPIVX', 0b101100): 'vsmul',
        ('OPIVX', 0b110000): 'vwaddu',
        ('OPIVX', 0b110001): 'vwadd',
        ('OPIVX', 0b110010): 'vwsubu',
        ('OPIVX', 0b110011): 'vwsub',
        ('OPIVX', 0b110100): 'vwaddu.w',
        ('OPIVX', 0b110101): 'vwadd.w',
        ('OPIVX', 0b110110): 'vwsubu.w',
        ('OPIVX', 0b110111): 'vwsub.w',
        
        # OPIVI
        ('OPIVI', 0b000000): 'vadd',
        ('OPIVI', 0b000011): 'vrsub',
        ('OPIVI', 0b001001): 'vand',
        ('OPIVI', 0b001010): 'vor',
        ('OPIVI', 0b001011): 'vxor',
        ('OPIVI', 0b001100): 'vrgather',
        ('OPIVI', 0b001110): 'vslideup',
        ('OPIVI', 0b001111): 'vslidedown',
        ('OPIVI', 0b010000): 'vadc',
        ('OPIVI', 0b010001): 'vmadc',
        ('OPIVI', 0b010111): 'vmerge',
        ('OPIVI', 0b011000): 'vmseq',
        ('OPIVI', 0b011001): 'vmsne',
        ('OPIVI', 0b011010): 'vmsleu',
        ('OPIVI', 0b011011): 'vmsle',
        ('OPIVI', 0b011110): 'vmsgtu',
        ('OPIVI', 0b011111): 'vmsgt',
        ('OPIVI', 0b100000): 'vsaddu',
        ('OPIVI', 0b100001): 'vsadd',
    }
    
    return opcode_map.get((category, funct6))


def get_shift_mnemonic(funct6: int, category: str) -> Optional[str]:
    """
    Get mnemonic for shift instructions.
    
    Returns the instruction mnemonic or None if not found
    """
    shift_map = {
        ('OPIVV', 0b100101): 'vsll',
        ('OPIVV', 0b101000): 'vsrl',
        ('OPIVV', 0b101001): 'vsra',
        ('OPIVV', 0b101010): 'vssrl',
        ('OPIVV', 0b101011): 'vssra',
        ('OPIVV', 0b101100): 'vnsrl',
        ('OPIVV', 0b101101): 'vnsra',
        ('OPIVV', 0b101110): 'vnclipu',
        ('OPIVV', 0b101111): 'vnclip',
        
        ('OPIVX', 0b100101): 'vsll',
        ('OPIVX', 0b101000): 'vsrl',
        ('OPIVX', 0b101001): 'vsra',
        ('OPIVX', 0b101010): 'vssrl',
        ('OPIVX', 0b101011): 'vssra',
        ('OPIVX', 0b101100): 'vnsrl',
        ('OPIVX', 0b101101): 'vnsra',
        ('OPIVX', 0b101110): 'vnclipu',
        ('OPIVX', 0b101111): 'vnclip',
        
        ('OPIVI', 0b100101): 'vsll',
        ('OPIVI', 0b101000): 'vsrl',
        ('OPIVI', 0b101001): 'vsra',
        ('OPIVI', 0b101010): 'vssrl',
        ('OPIVI', 0b101011): 'vssra',
        ('OPIVI', 0b101100): 'vnsrl',
        ('OPIVI', 0b101101): 'vnsra',
        ('OPIVI', 0b101110): 'vnclipu',
        ('OPIVI', 0b101111): 'vnclip',
    }
    
    return shift_map.get((category, funct6))


def get_multiply_mnemonic(funct6: int, category: str) -> Optional[str]:
    """
    Get mnemonic for multiply instructions.
    
    Returns the instruction mnemonic or None if not found
    """
    mul_map = {
        ('OPIVV', 0b100101): 'vmul',
        ('OPIVV', 0b100111): 'vmulh',
        ('OPIVV', 0b100110): 'vmulhu',
        ('OPIVV', 0b100100): 'vmulhsu',
        ('OPIVV', 0b101001): 'vmadd',
        ('OPIVV', 0b101011): 'vnmsub',
        ('OPIVV', 0b101101): 'vmacc',
        ('OPIVV', 0b101111): 'vnmsac',
        ('OPIVV', 0b111000): 'vwmulu',
        ('OPIVV', 0b111010): 'vwmulsu',
        ('OPIVV', 0b111011): 'vwmul',
        ('OPIVV', 0b111100): 'vwmaccu',
        ('OPIVV', 0b111101): 'vwmacc',
        ('OPIVV', 0b111110): 'vwmaccus',
        ('OPIVV', 0b111111): 'vwmaccsu',
        
        ('OPIVX', 0b100101): 'vmul',
        ('OPIVX', 0b100111): 'vmulh',
        ('OPIVX', 0b100110): 'vmulhu',
        ('OPIVX', 0b100100): 'vmulhsu',
        ('OPIVX', 0b101001): 'vmadd',
        ('OPIVX', 0b101011): 'vnmsub',
        ('OPIVX', 0b101101): 'vmacc',
        ('OPIVX', 0b101111): 'vnmsac',
        ('OPIVX', 0b111000): 'vwmulu',
        ('OPIVX', 0b111010): 'vwmulsu',
        ('OPIVX', 0b111011): 'vwmul',
        ('OPIVX', 0b111100): 'vwmaccu',
        ('OPIVX', 0b111101): 'vwmacc',
        ('OPIVX', 0b111110): 'vwmaccus',
        ('OPIVX', 0b111111): 'vwmaccsu',
    }
    
    return mul_map.get((category, funct6))


def get_floating_point_mnemonic(funct6: int, category: str) -> Optional[str]:
    """
    Get mnemonic for floating-point instructions.
    
    Returns the instruction mnemonic or None if not found
    """
    fp_map = {
        ('OPFVV', 0b000000): 'vfadd',
        ('OPFVV', 0b000010): 'vfsub',
        ('OPFVV', 0b000100): 'vfmin',
        ('OPFVV', 0b000101): 'vfmax',
        ('OPFVV', 0b000110): 'vfsgnj',
        ('OPFVV', 0b000111): 'vfsgnjn',
        ('OPFVV', 0b001000): 'vfsgnjx',
        ('OPFVV', 0b001010): 'vfmul',
        ('OPFVV', 0b001100): 'vfdiv',
        ('OPFVV', 0b001110): 'vfrdiv',
        ('OPFVV', 0b010000): 'vfmacc',
        ('OPFVV', 0b010001): 'vfnmacc',
        ('OPFVV', 0b010010): 'vfmsac',
        ('OPFVV', 0b010011): 'vfnmsac',
        ('OPFVV', 0b010100): 'vfmadd',
        ('OPFVV', 0b010101): 'vfnmadd',
        ('OPFVV', 0b010110): 'vfmsub',
        ('OPFVV', 0b010111): 'vfnmsub',
        ('OPFVV', 0b011000): 'vfmul',
        ('OPFVV', 0b011010): 'vfredosum',
        ('OPFVV', 0b011011): 'vfredusum',
        ('OPFVV', 0b011100): 'vfredmax',
        ('OPFVV', 0b011101): 'vfredmin',
        ('OPFVV', 0b100000): 'vfwmacc',
        ('OPFVV', 0b100001): 'vfwnmacc',
        ('OPFVV', 0b100010): 'vfwmsac',
        ('OPFVV', 0b100011): 'vfwnmsac',
        ('OPFVV', 0b100100): 'vfwmul',
        ('OPFVV', 0b101000): 'vfadd',
        ('OPFVV', 0b101010): 'vfsub',
        ('OPFVV', 0b101100): 'vfwadd',
        ('OPFVV', 0b101101): 'vfwsub',
        ('OPFVV', 0b101110): 'vfwadd',
        ('OPFVV', 0b101111): 'vfwsub',
        ('OPFVV', 0b110000): 'vfmul',
        ('OPFVV', 0b110100): 'vfwmul',
        ('OPFVV', 0b110110): 'vfwmul',
        ('OPFVV', 0b111000): 'vfdiv',
        ('OPFVV', 0b111010): 'vfrdiv',
        ('OPFVV', 0b111100): 'vfwmacc',
        ('OPFVV', 0b111101): 'vfwnmacc',
        ('OPFVV', 0b111110): 'vfwmsac',
        ('OPFVV', 0b111111): 'vfwnmsac',
        
        ('OPFVF', 0b000000): 'vfadd',
        ('OPFVF', 0b000010): 'vfsub',
        ('OPFVF', 0b000100): 'vfmin',
        ('OPFVF', 0b000101): 'vfmax',
        ('OPFVF', 0b000110): 'vfsgnj',
        ('OPFVF', 0b000111): 'vfsgnjn',
        ('OPFVF', 0b001000): 'vfsgnjx',
        ('OPFVF', 0b001010): 'vfmul',
        ('OPFVF', 0b001100): 'vfdiv',
        ('OPFVF', 0b001110): 'vfrdiv',
        ('OPFVF', 0b010000): 'vfmacc',
        ('OPFVF', 0b010001): 'vfnmacc',
        ('OPFVF', 0b010010): 'vfmsac',
        ('OPFVF', 0b010011): 'vfnmsac',
        ('OPFVF', 0b010100): 'vfmadd',
        ('OPFVF', 0b010101): 'vfnmadd',
        ('OPFVF', 0b010110): 'vfmsub',
        ('OPFVF', 0b010111): 'vfnmsub',
        ('OPFVF', 0b100000): 'vfwmacc',
        ('OPFVF', 0b100001): 'vfwnmacc',
        ('OPFVF', 0b100010): 'vfwmsac',
        ('OPFVF', 0b100011): 'vfwnmsac',
        ('OPFVF', 0b100100): 'vfwmul',
        ('OPFVF', 0b101000): 'vfadd',
        ('OPFVF', 0b101010): 'vfsub',
        ('OPFVF', 0b101100): 'vfwadd',
        ('OPFVF', 0b101101): 'vfwsub',
        ('OPFVF', 0b101110): 'vfwadd',
        ('OPFVF', 0b101111): 'vfwsub',
        ('OPFVF', 0b110000): 'vfmul',
        ('OPFVF', 0b110100): 'vfwmul',
        ('OPFVF', 0b110110): 'vfwmul',
        ('OPFVF', 0b111000): 'vfdiv',
        ('OPFVF', 0b111010): 'vfrdiv',
        ('OPFVF', 0b111100): 'vfwmacc',
        ('OPFVF', 0b111101): 'vfwnmacc',
        ('OPFVF', 0b111110): 'vfwmsac',
        ('OPFVF', 0b111111): 'vfwnmsac',
    }
    
    return fp_map.get((category, funct6))


def get_reduction_mnemonic(funct6: int, category: str) -> Optional[str]:
    """
    Get mnemonic for reduction instructions.
    
    Returns the instruction mnemonic or None if not found
    """
    red_map = {
        ('OPIVV', 0b000000): 'vredsum',
        ('OPIVV', 0b000001): 'vredand',
        ('OPIVV', 0b000010): 'vredor',
        ('OPIVV', 0b000011): 'vredxor',
        ('OPIVV', 0b000100): 'vredminu',
        ('OPIVV', 0b000101): 'vredmin',
        ('OPIVV', 0b000110): 'vredmaxu',
        ('OPIVV', 0b000111): 'vredmax',
        ('OPIVX', 0b000000): 'vredsum',
        ('OPIVX', 0b000001): 'vredand',
        ('OPIVX', 0b000010): 'vredor',
        ('OPIVX', 0b000011): 'vredxor',
        ('OPIVX', 0b000100): 'vredminu',
        ('OPIVX', 0b000101): 'vredmin',
        ('OPIVX', 0b000110): 'vredmaxu',
        ('OPIVX', 0b000111): 'vredmax',
    }
    
    return red_map.get((category, funct6))


def get_mask_mnemonic(funct6: int, category: str) -> Optional[str]:
    """
    Get mnemonic for mask instructions.
    
    Returns the instruction mnemonic or None if not found
    """
    mask_map = {
        ('OPMVV', 0b010000): 'vadc',
        ('OPMVV', 0b010010): 'vmsbc',
        ('OPMVV', 0b010100): 'vmerge',
        ('OPMVV', 0b010111): 'vmv',
        ('OPMVV', 0b011000): 'vmseq',
        ('OPMVV', 0b011001): 'vmsne',
        ('OPMVV', 0b011010): 'vmsltu',
        ('OPMVV', 0b011011): 'vmslt',
        ('OPMVV', 0b011100): 'vmsleu',
        ('OPMVV', 0b011101): 'vmsle',
        ('OPMVV', 0b011110): 'vmsgtu',
        ('OPMVV', 0b011111): 'vmsgt',
        ('OPMVX', 0b010000): 'vadc',
        ('OPMVX', 0b010010): 'vmsbc',
        ('OPMVX', 0b010100): 'vmerge',
        ('OPMVX', 0b010111): 'vmv',
        ('OPMVX', 0b011000): 'vmseq',
        ('OPMVX', 0b011001): 'vmsne',
        ('OPMVX', 0b011010): 'vmsltu',
        ('OPMVX', 0b011011): 'vmslt',
        ('OPMVX', 0b011100): 'vmsleu',
        ('OPMVX', 0b011101): 'vmsle',
        ('OPMVX', 0b011110): 'vmsgtu',
        ('OPMVX', 0b011111): 'vmsgt',
    }
    
    return mask_map.get((category, funct6))


def get_config_mnemonic(funct6: int, vs2: int, vs1_rs1: int) -> Optional[str]:
    """
    Get mnemonic for configuration instructions.
    
    Returns the instruction mnemonic or None if not found
    """
    if funct6 == 0b000000:
        if vs2 == 0b11111:
            return 'vsetvli'
        else:
            return 'vsetvl'
    elif funct6 == 0b100000:
        return 'vsetivli'
    
    return None


def get_mnemonic(funct6: int, category: str, vs2: int, vs1_rs1: int, vd_rd: int = None) -> Optional[str]:
    """
    Get instruction mnemonic from funct6 and category.
    
    Uses additional fields (vd_rd) when provided to better distinguish between
    instructions that share the same funct6 value.
    
    Args:
        funct6: The funct6 field
        category: The operand category
        vs2: The vs2 field
        vs1_rs1: The vs1/rs1 field
        vd_rd: Optional destination register field (helps distinguish reductions)
    
    Returns:
        The instruction mnemonic or None if not found
    """
    if category == 'OPCFG':
        return get_config_mnemonic(funct6, vs2, vs1_rs1)

    elif category in ('OPFVV', 'OPFVF'):
        return get_floating_point_mnemonic(funct6, category)

    elif category in ('OPMVV', 'OPMVX'):
        mnemonic = get_mask_mnemonic(funct6, category)
        if mnemonic:
            return mnemonic

        # Some assemblers encode integer ops (e.g., vmul.vv) with funct3=010/110.
        # Fall back to the equivalent integer category and try again.
        if category == 'OPMVV' and funct6 == 0b100101:
            return 'vmul'

        category = 'OPIVV' if category == 'OPMVV' else 'OPIVX'

    if category in ('OPIVV', 'OPIVX', 'OPIVI'):

        # Don't change the order of these checks, they are in the most error free order. 

        mnemonic = get_shift_mnemonic(funct6, category)
        if mnemonic:
            return mnemonic
        
        multiply_arithmetic_conflict_range = range(0b100000, 0b100111 + 1)
        
        if funct6 in multiply_arithmetic_conflict_range:
            if category == 'OPIVV':

                # For OPIVV, multiply takes priority (per RISC-V spec)
                mnemonic = get_multiply_mnemonic(funct6, category)
                if mnemonic:
                    return mnemonic

            # For OPIVX and OPIVI, arithmetic takes priority
            mnemonic = get_integer_arithmetic_mnemonic(funct6, category)
            if mnemonic:
                return mnemonic

            # Fallback to multiply (shouldn't normally match for OPIVX/OPIVI)
            mnemonic = get_multiply_mnemonic(funct6, category)
            if mnemonic:
                return mnemonic
        else:

            # For non-conflicting funct6 values, check multiply first, then arithmetic
            mnemonic = get_multiply_mnemonic(funct6, category)
            if mnemonic:
                return mnemonic
            
            mnemonic = get_integer_arithmetic_mnemonic(funct6, category)
            if mnemonic:
                return mnemonic
        
        # 3. Check reduction instructions last (they share funct6 with arithmetic)
        reduction_funct6 = {0b000000, 0b000001, 0b000010, 0b000011,
                           0b000100, 0b000101, 0b000110, 0b000111}
        if funct6 in reduction_funct6:
            mnemonic = get_reduction_mnemonic(funct6, category)
            if mnemonic:
                return mnemonic

        return None
    else:
        return None


def decode_vtype(vtype: int) -> str:
    """
    Decode vtype field into SEW, LMUL, ta, ma format.
    
    vtype bits [30:20]:
    - bits [30:29]: vill (illegal if != 0)
    - bit [28]: vma (mask agnostic)
    - bit [27]: vta (tail agnostic)
    - bits [26:25]: vsew (SEW encoding: 0=e8, 1=e16, 2=e32, 3=e64)
    - bits [24:22]: vlmul (LMUL encoding: 0=m1, 1=m2, 2=m4, 3=m8, 4=mf2, 5=mf4, 6=mf8, 7=reserved)
    
    Returns formatted string like "e64, m1, ta, ma"
    """
    vill = (vtype >> 9) & 0x3
    if vill != 0:
        return "ILLEGAL"
    
    vma = (vtype >> 8) & 0x1
    vta = (vtype >> 7) & 0x1
    vsew = (vtype >> 5) & 0x3
    vlmul_raw = vtype & 0x7
    
    # Decode SEW
    sew_map = {0: "e8", 1: "e16", 2: "e32", 3: "e64"}
    sew = sew_map.get(vsew, f"e{8 << vsew}")
    
    # Decode LMUL
    lmul_map = {
        0: "m1", 1: "m2", 2: "m4", 3: "m8",
        4: "mf2", 5: "mf4", 6: "mf8"
    }
    lmul = lmul_map.get(vlmul_raw, f"m{vlmul_raw}")
    
    # Decode ta/ma
    ta = "ta" if vta == 0 else "tu"
    ma = "ma" if vma == 0 else "mu"
    
    return f"{sew}, {lmul}, {ta}, {ma}"


def get_load_store_mnemonic(opcode: int, funct3: int, width: int, mop: int, mew: int, nf: int) -> Optional[str]:
    """
    Get mnemonic for load/store instructions.
    
    Args:
        opcode: Instruction opcode (0x07 for load, 0x27 for store)
        funct3: funct3 field
        width: width field (bits 14:12) - encodes memory access width
        mop: memory operation type (bits 27:26)
        mew: memory element width extension (bit 28)
        nf: number of fields (bits 31:29)
    
    Returns mnemonic or None
    """
    is_load = (opcode == 0x07)
    is_store = (opcode == 0x27)
    
    if not (is_load or is_store):
        return None
    
    # For vector unit-stride loads/stores (mop=0b00)
    # funct3 (width field bits 14:12) encodes EEW
    if mop == 0b00:
        # width encoding for vector loads/stores:
        # 0b000 = 8-bit
        # 0b101 = 16-bit  
        # 0b110 = 32-bit
        # 0b111 = 64-bit
        width_map = {
            0b000: ("vle8", "vse8"),
            0b101: ("vle16", "vse16"),
            0b110: ("vle32", "vse32"),
            0b111: ("vle64", "vse64"),
        }
        mnemonic_pair = width_map.get(funct3)
        if mnemonic_pair:
            return mnemonic_pair[0] if is_load else mnemonic_pair[1]
    
    # For standard scalar loads/stores
    if funct3 != 0b111:
        width_map = {
            0b000: "lb" if is_load else "sb",
            0b001: "lh" if is_load else "sh",
            0b010: "lw" if is_load else "sw",
            0b011: "ld" if is_load else "sd",
        }
        return width_map.get(funct3)
    
    return None


def format_load_store(instruction: int) -> str:
    """
    Format load/store instruction.
    
    Format: vle64.v v1, (x1)
    """
    opcode = instruction & 0x7F
    funct3 = (instruction >> 12) & 0x7
    vd_rd = (instruction >> 7) & 0x1F
    rs1 = (instruction >> 15) & 0x1F
    vm = (instruction >> 25) & 0x1
    mop = (instruction >> 26) & 0x3
    mew = (instruction >> 28) & 0x1
    nf = (instruction >> 29) & 0x7
    
    mnemonic = get_load_store_mnemonic(opcode, funct3, 0, mop, mew, nf)
    if mnemonic is None:
        return "UNKNOWN"
    
    # Add suffix - vector loads use .v suffix
    if mop == 0b00:  # vector unit-stride
        suffix = ".v"
    else:
        suffix = ""
    full_mnemonic = f"{mnemonic}{suffix}"
    
    # Format: vle64.v v1, (x1) or vle64.v v1, (x1), v0.t
    if vm == 0:
        return f"{full_mnemonic} v{vd_rd}, (x{rs1}), v0.t"
    else:
        return f"{full_mnemonic} v{vd_rd}, (x{rs1})"


def sign_extend_imm5(imm5: int) -> int:
    """
    Sign extend a 5-bit immediate value.
    
    Returns the sign-extended 32-bit integer (as a signed value)
    """
    imm5 = imm5 & 0x1F
    # Sign extend: if bit 4 is set, treat as negative
    if imm5 & 0x10:
        # Sign extend: convert to negative by subtracting 32
        return imm5 - 32
    return imm5


def format_instruction(mnemonic: str, category: str, vd_rd: int, vs2: int,
                      vs1_rs1: int, imm5: int, vm: int) -> str:
    """
    Format instruction into human-readable string.
    
    Returns the formatted instruction string
    """
    # Determine suffix based on category
    suffix_map = {
        'OPIVV': '.vv',
        'OPIVX': '.vx',
        'OPIVI': '.vi',
        'OPFVV': '.vv',
        'OPFVF': '.vf',
        'OPMVV': '.vv',
        'OPMVX': '.vx',
        'OPCFG': '',
    }
    
    suffix = suffix_map.get(category, '')
    full_mnemonic = f"{mnemonic}{suffix}"
    
    # Configuration instructions have special formatting
    if category == 'OPCFG':
        if mnemonic == 'vsetvl':
            return f"{full_mnemonic} x{vd_rd}, x{vs1_rs1}, x{vs2}"

        elif mnemonic == 'vsetivli':
            return f"{full_mnemonic} x{vd_rd}, {imm5}, {vs2}"

    # Vector-immediate format
    elif category == 'OPIVI':
        imm_val = sign_extend_imm5(imm5)
        if vm == 0:
            return f"{full_mnemonic} v{vd_rd}, v{vs2}, {imm_val}, v0.t"
        else:
            return f"{full_mnemonic} v{vd_rd}, v{vs2}, {imm_val}"

    # Vector-scalar format
    elif category == 'OPIVX' or category == 'OPFVF' or category == 'OPMVX':
        if vm == 0:
            return f"{full_mnemonic} v{vd_rd}, v{vs2}, x{vs1_rs1}, v0.t"
        else:
            return f"{full_mnemonic} v{vd_rd}, v{vs2}, x{vs1_rs1}"

    # Vector-vector format
    elif category == 'OPIVV' or category == 'OPFVV' or category == 'OPMVV':
        if vm == 0:
            return f"{full_mnemonic} v{vd_rd}, v{vs2}, v{vs1_rs1}, v0.t"
        else:
            return f"{full_mnemonic} v{vd_rd}, v{vs2}, v{vs1_rs1}"

    # Fallback format
    else:
        return f"{full_mnemonic} v{vd_rd}, v{vs2}, v{vs1_rs1}"
    
    return "UNKNOWN_FORMAT"


def disassemble_rvv(instruction: int) -> str:
    """
    Disassemble a RISC-V Vector Extension instruction.

    Args: instruction - 32-bit instruction word as integer
    
    Returns the disassembled instruction string or "UNKNOWN" if the instruction is not a valid RVV instruction
    """
    opcode = instruction & 0x7F
    
    if opcode == 0x07 or opcode == 0x27:
        return format_load_store(instruction)
    
    if opcode != 0x57:
        return "UNKNOWN"
    
    funct3 = (instruction >> 12) & 0x7
    category = get_operand_category(funct3)
    if category is None:
        return "UNKNOWN"
    
    if category == 'OPCFG':
        vtype = (instruction >> 20) & 0x7FF
        vs2_lower = vtype & 0x1F
        funct6_upper = (instruction >> 26) & 0x3F
        
        vd_rd = (instruction >> 7) & 0x1F
        vs1_rs1 = (instruction >> 15) & 0x1F
        
        if funct6_upper == 0b100000:
            imm5 = vs1_rs1
            vs2 = (vtype >> 5) & 0x1F
            return f"vsetivli x{vd_rd}, {imm5}, {vs2}"
        
        elif vs2_lower == 0b11111:
            vtype_str = decode_vtype(vtype)
            return f"vsetvli x{vd_rd}, x{vs1_rs1}, {vtype_str}"
        
        else:
            opcode, funct6, vm, vs2, vs1_rs1, funct3, vd_rd, imm5 = extract_fields(instruction)
            mnemonic = get_mnemonic(funct6, category, vs2, vs1_rs1, vd_rd)
            if mnemonic:
                return format_instruction(mnemonic, category, vd_rd, vs2, vs1_rs1, imm5, vm)
            # If get_mnemonic returns None, try to decode as vsetvli anyway if it looks like one
            # (some encodings might not follow the exact pattern)
            vtype_str = decode_vtype(vtype)
            if vtype_str != "ILLEGAL":
                return f"vsetvli x{vd_rd}, x{vs1_rs1}, {vtype_str}"
    
    opcode, funct6, vm, vs2, vs1_rs1, funct3, vd_rd, imm5 = extract_fields(instruction)
    
    mnemonic = get_mnemonic(funct6, category, vs2, vs1_rs1, vd_rd)
    if mnemonic is None:
        return "UNKNOWN"
    
    return format_instruction(mnemonic, category, vd_rd, vs2, vs1_rs1, imm5, vm)


def main():
    """
    Main entry point for command-line usage.
    
    Usage:
        python rvv_disassembler.py <instruction>
        python rvv_disassembler.py 0x5e0ec057
        python rvv_disassembler.py 1578102871
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python rvv_disassembler.py <instruction>")
        print("  instruction can be in hex (0x...) or decimal format")
        print("\nExamples:")
        print("  python rvv_disassembler.py 0x5e0ec057")
        print("  python rvv_disassembler.py 1578102871")
        sys.exit(1)
    
    instruction_str = sys.argv[1].strip()
    
    try:
        if instruction_str.startswith('0x') or instruction_str.startswith('0X'):
            instruction = int(instruction_str, 16)
        else:
            instruction = int(instruction_str, 10)
        
        instruction = instruction & 0xFFFFFFFF
        
        result = disassemble_rvv(instruction)
        print(result)
        
    except ValueError as e:
        print(f"Error: Invalid instruction format '{instruction_str}'")
        print(f"  {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

