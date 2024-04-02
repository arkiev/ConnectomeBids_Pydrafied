from ast import alias
import os
import typing as ty
import pydra  
from pydra import Workflow, mark, ShellCommandTask
from pydra.engine.specs import File
from pydra.tasks.mrtrix3.v3_0 import TransformConvert,MrTransform #mrconvert, mrgrid, mrconvert, dwiextract, mrcalc, mrmath, dwibiasnormmask, mrthreshold
from pydra.tasks.fsl.auto  import EpiReg
from pydra.engine.specs import SpecInfo, BaseSpec, ShellSpec, ShellOutSpec
from fileformats.medimage import NiftiGzXBvec, NiftiGz
from fileformats.medimage_mrtrix3 import ImageFormat
from pathlib import Path

# Define the path and output_path variables
output_path = '/Users/arkievdsouza/git/ConnectomeBids_Pydrafied/outputs/carriage3/'

# Define the input_spec for the workflow
input_spec = {"mean_bzero": File, "t1": File,"t1_brain": File,"wmseg": File}
output_spec = {"warp": File}

# Create a workflow 
wf = Workflow(name='connectomebids_carriage3_wf', input_spec=input_spec, cache_dir=output_path, output_spec=output_spec) 

# Step 9: Perform DWI->T1 registration
wf.add(
    EpiReg(
        epi=wf.lzin.mean_bzero,
        t1_head=wf.lzin.t1,
        t1_brain=wf.lzin.t1_brain,
        wmseg=wf.lzin.wmseg,
        # fullwarp="dwi2T1_warp.nii.gz",
        out_base="epi2struct",
        name="epi_reg_task", 
        matrix="epi2struct.mat",
    )
)

# # transformconvert task 
wf.add(
    TransformConvert(
        input=wf.epi_reg_task.lzout.matrix,
        operation="flirt_import",
        flirt_in=wf.lzin.mean_bzero,
        flirt_ref=wf.lzin.t1_brain,
        out_file="epi2struct_mrtrix.txt",
        name="transformconvert_task", 

    )
)

# Step 10: Apply transform (to get T1 in DWI space - test)
wf.add(
    MrTransform(
        name="transformT1_task",
        in_file=wf.lzin.t1,
        inverse=True,
        out_file="T1_registered.mif",
        linear=wf.transformconvert_task.lzout.out_file,
        strides=wf.lzin.mean_bzero,
    )

)

wf.set_output(("connectomebids_carriage3_wf", wf.transformT1_task.lzout.out_file))

# ########################
# # Execute the workflow #
# ########################

# result = wf(
#     # dwi_preproc_mif="/Users/arkievdsouza/git/ConnectomeBids_Pydrafied/outputs/carriage3/dwi_biasnorm.mif",
#     # FS_dir="/Users/arkievdsouza/Desktop/ConnectomeBids/output/MRtrix3_connectome-participant_hcpmmp1/sub-01/scratch/freesurfer/",
#     t1="/Users/arkievdsouza/git/ConnectomeBids_Pydrafied/outputs/carriage3/t1.nii.gz",
#     t1_brain="/Users/arkievdsouza/git/ConnectomeBids_Pydrafied/outputs/carriage3/t1brain.nii.gz",
#     wmseg="/Users/arkievdsouza/git/ConnectomeBids_Pydrafied/outputs/carriage3/t1brain_wmseg.nii.gz",
#     mean_bzero="/Users/arkievdsouza/git/ConnectomeBids_Pydrafied/outputs/carriage3/dwi_meanbzero.nii.gz",
#     plugin="serial",
# )


result = wf(
    # dwi_preproc_mif="/Users/arkievdsouza/git/ConnectomeBids_Pydrafied/outputs/carriage3/dwi_biasnorm.mif",
    # FS_dir="/Users/arkievdsouza/Desktop/ConnectomeBids/output/MRtrix3_connectome-participant_hcpmmp1/sub-01/scratch/freesurfer/",
    t1='/Users/arkievdsouza/Library/CloudStorage/OneDrive-TheUniversityofSydney(Staff)/sampledata/t1.nii.gz',
    t1_brain='/Users/arkievdsouza/Library/CloudStorage/OneDrive-TheUniversityofSydney(Staff)/sampledata/brain.nii.gz',
    wmseg='/Users/arkievdsouza/Library/CloudStorage/OneDrive-TheUniversityofSydney(Staff)/sampledata/wm_bin.nii.gz',
    mean_bzero='/Users/arkievdsouza/Library/CloudStorage/OneDrive-TheUniversityofSydney(Staff)/sampledata/mean_bzero.nii.gz',
    plugin="serial",
)