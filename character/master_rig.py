"""Engine-neutral semantic rig contract; native rigs require explicit mapping."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Bone:
    name: str
    parent: str | None

MASTER_RIG = (
    Bone('Hips', None), Bone('Spine', 'Hips'), Bone('Chest', 'Spine'),
    Bone('UpperChest', 'Chest'), Bone('Neck', 'UpperChest'), Bone('Head', 'Neck'),
    Bone('LeftShoulder', 'UpperChest'), Bone('LeftUpperArm', 'LeftShoulder'),
    Bone('LeftLowerArm', 'LeftUpperArm'), Bone('LeftHand', 'LeftLowerArm'),
    Bone('RightShoulder', 'UpperChest'), Bone('RightUpperArm', 'RightShoulder'),
    Bone('RightLowerArm', 'RightUpperArm'), Bone('RightHand', 'RightLowerArm'),
    Bone('LeftUpperLeg', 'Hips'), Bone('LeftLowerLeg', 'LeftUpperLeg'),
    Bone('LeftFoot', 'LeftLowerLeg'), Bone('LeftToes', 'LeftFoot'),
    Bone('RightUpperLeg', 'Hips'), Bone('RightLowerLeg', 'RightUpperLeg'),
    Bone('RightFoot', 'RightLowerLeg'), Bone('RightToes', 'RightFoot'),
)

def validate_rig(native_parents: dict[str, str | None], native_to_semantic: dict[str, str]) -> list[str]:
    """Return errors for missing bones, ambiguous mappings, and incorrect mapped parents.

    Does not assume UE MetaHuman, UMA, and VRM native bone names are identical.
    """
    reverse: dict[str, str] = {}
    errors: list[str] = []
    for native, semantic in native_to_semantic.items():
        if native not in native_parents:
            errors.append(f'missing native bone: {native}')
        if semantic in reverse:
            errors.append(f'duplicate semantic bone: {semantic}')
        reverse[semantic] = native
    for bone in MASTER_RIG:
        native = reverse.get(bone.name)
        if native is None:
            errors.append(f'missing semantic bone: {bone.name}')
        elif native in native_parents and bone.parent is not None:
            parent_native = reverse.get(bone.parent)
            if parent_native is not None and native_parents[native] != parent_native:
                errors.append(f'incorrect parent: {bone.name}')
    return errors
