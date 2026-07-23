# references/ — routing table

Open-source projects we learn from or replicate. **The CLONE folders below are already checked out on disk here** — gitignored (so `git`/`git ls-files` won't show them), but present: `ls references/` to confirm. Read them directly.

- **CLONE** — study to subsume/replace; present at `references/<name>/` (gitignored). Re-clone only if a folder is missing: `git clone <url> references/<name>`.
- **POINT** — kept as imports; read in the active project's `Packages/<id>/` (`vrc-get resolve` if absent).

`Pri`: H first · M reference · L niche/overlapped.

## Find by capability

Match your task → project (`file`).

**Author animators in code**
- Generate controller / layers / states / clips / blend-trees → `av3-animator-as-code` (`AacV1.Create`, `AacFl*`)
- VRC behaviors & built-in params in codegen → `animator-as-code-vrchat` (`AacVRCExtensions.cs`, `AacAv3`)
- Create Modular Avatar components in code → `modular-avatar-as-code` (`MaAc.cs`)
- Run codegen at build as an NDMF plugin → `prefabulous-avatar` (`PrefabulousAacPlugin.cs`; blend-trees `…FaceTrackingExtensionsPlugin.cs` MegaTree)

**Edit an existing animator**
- Merge/clone a controller, remap params, fix Write Defaults → `av3manager` (`AnimatorCloner.cs`, `AV3ManagerFunctions.cs`)
- Remove orphaned sub-assets (states/transitions/blend-trees) → `controllercleaner` (`ControllerCleaner.cs`)
- Augment menu/param inspectors (study-only, GPL) → `vrcsdkplus`

**Import / fork / normalize a vendor avatar**
- Deep-copy a vendor avatar + rewire refs → `AvatarFork` (`AFCopy{Controller,Material,Expression}.cs`)
- Rebind mesh bones after armature change → `AvatarFork` (`AFBoneRemapper.cs`)
- Rewrite GUIDs/refs when duplicating prefabs/FBX → `Instancer` (`FixPrefabReferences()`)
- Repath clip bindings after move/rename → `RepathClips`/`OwnControllerClips` (vrc-unity-tools; stock `AnimationUtility` idiom extracted MIT from `animationrepathing`)
- Copy components between avatars; auto visemes/eyes/viewpoint/bounds → `PumkinsAvatarTools` (`GenericCopier.cs`, `FillVisemes`/`FillEyeBones`)

**Constraints**
- Convert/bake Unity↔VRC constraints; weld to a skinned mesh → `constraint-tools` (`SkinnedMeshConstraintBuilderEditor.cs`)

**Network sync & contacts**
- Sync an object's world position/rotation across the network (contacts+drivers, float→bool packing for cheap params) → `Custom-Object-Sync` (`CustomObjectSyncCreator.cs`, `ControllerGenerationMethods.cs`)
- Attach an object to another player's contact (6 proximity contacts + parent constraint) → `Contact-Tracker` (`Contact Tracker.prefab`, `Contact Tracker FX.controller`)

**Blender prep (headless bpy)**
- Shape-key-safe rest-pose bake → `Cats` (`tools/armature_manual.py` `PoseToRest`); FBX export `tools/importer.py`; visemes `tools/viseme.py`; eyes `tools/eyetracking.py`; fix model `tools/armature.py`

**Optimization techniques (learn, don't import)**
- Mesh/material merge, atlas, blendshape prune, shader-rewrite → `d4rkAvatarOptimizer` (`d4rkAvatarOptimizer.cs`, `ShaderAnalyzer.cs`); `anatawa12 AvatarOptimizer` (`Processors/TraceAndOptimize/`, `ObjectMapping/`)

**Test & ship**
- Verify in Play Mode; drive params over OSC (9000/9001) → `av3emulator` (`LyumaAv3Runtime`, `LyumaAv3Osc`)
- Inspect/drive expression menus in-editor → `gesture-manager` (`ModuleVrc3`, `Vrc3Param`)
- Build + upload programmatically → `continuous-avatar-uploader` (`Uploader`, `VRCApi`)

**Materials & shaders**
- Manipulate Poiyomi materials (animate locked props via `<prop>Animated` tag) → `poiyomi` (`ShaderOptimizer`)
- Manipulate lilToon materials → `liltoon` (`Editor/lilMaterialProperties.cs`)
- Make a shader react to audio → `audiolink` (`AudioLink.cginc`, `ALPASS_*`)

**Learn the concepts (prose knowledge base, not code)**
- Avatar 3.0 + Unity-animation reference — Write-Defaults, AAPs, DBT-Combining, Network-Sync, Scale-Friendly, Benchmarks, PhysBones/Contacts/puppets → `VRCSchool` (`docs/{Unity-Animations,Avatars,Other}/*.md`, images inline as sibling `.png`)

**Read the data model / pipeline (don't replicate)**
- Avatar descriptor, menus/params, PhysBones, contacts, constraints → `com.vrchat.avatars`
- Non-destructive build framework to respect → `ndmf` (`BuildPhase`, `Plugin<T>`/`Pass<T>`); MA components `modular-avatar`; VRCFury components `vrcfury` (`FeatureOrder.cs`)

## CLONE

| Project | Pri | License |
|---|---|---|
| [av3-animator-as-code](https://github.com/hai-vr/av3-animator-as-code) | H | MIT |
| [animator-as-code-vrchat](https://github.com/hai-vr/animator-as-code-vrchat) | H | MIT |
| [modular-avatar-as-code](https://github.com/hai-vr/modular-avatar-as-code) | H | MIT |
| [prefabulous-avatar](https://github.com/hai-vr/prefabulous-avatar) | H | MIT (needs out-of-tree `.universal` sibling) |
| [PumkinsAvatarTools](https://github.com/rurre/PumkinsAvatarTools) | H | MIT |
| [AvatarFork](https://github.com/fkrisi11/AvatarFork) | H | MIT |
| [Cats-Blender-Plugin](https://github.com/teamneoneko/Cats-Blender-Plugin) | H | **GPL-3.0 — clean-room only** |
| [constraint-tools](https://github.com/hai-vr/constraint-tools) | M | MIT |
| [Instancer](https://github.com/VRLabs/Instancer) | M | MIT |
| [Custom-Object-Sync](https://github.com/Ryan6-VRC/Custom-Object-Sync) | M | MIT |
| [Contact-Tracker](https://github.com/VRLabs/Contact-Tracker) | M | MIT |
| [VRCSchool](https://github.com/VRLabs/VRCSchool) | M | MIT — prose knowledge base, read `docs/*.md` |

## POINT

| Package | Pri | License |
|---|---|---|
| `com.vrchat.avatars` (+ `com.vrchat.base`) | H | Proprietary SDK — gitignored, `vrc-get`-restored |
| [`nadena.dev.modular-avatar`](https://github.com/bdunderscore/modular-avatar) | H | MIT |
| [`nadena.dev.ndmf`](https://github.com/bdunderscore/ndmf) | H | MIT |
| [`com.vrcfury.vrcfury`](https://github.com/VRCFury/VRCFury) | H | NON-FOSS — don't vendor |
| [`lyuma.av3emulator`](https://github.com/lyuma/Av3Emulator) | H | MIT |
| [`dev.vrlabs.av3manager`](https://github.com/VRLabs/Avatars-3.0-Manager) | H | MIT |
| [`d4rkpl4y3r.d4rkavataroptimizer`](https://github.com/d4rkc0d3r/d4rkAvatarOptimizer) | M | MIT |
| [`com.anatawa12.avatar-optimizer`](https://github.com/anatawa12/AvatarOptimizer) | M | MIT |
| [`com.anatawa12.continuous-avatar-uploader`](https://github.com/anatawa12/ContinuousAvatarUploader) | M | MIT |
| [`dev.vrlabs.controllercleaner`](https://github.com/VRLabs/ControllerCleaner) | M | MIT |
| [`com.poiyomi.toon`](https://github.com/poiyomi/PoiyomiToonShader) | M | MIT |
| [`jp.lilxyzw.liltoon`](https://github.com/lilxyzw/lilToon) | M | MIT |
| [`com.hfcred.animationrepathing`](https://github.com/hfcRed/Animation-Repathing) | M | MIT |
| [`vrchat.blackstartx.gesture-manager`](https://github.com/BlackStartx/VRC-Gesture-Manager) | L | MIT |
| [`dev.vrlabs.vrcsdkplus`](https://github.com/VRLabs/VRCSDKPlus) | L | GPL-3.0 — study only |
| [`com.llealloo.audiolink`](https://github.com/llealloo/audiolink) | L | MIT |
