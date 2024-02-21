from ast import alias
import os
import typing as ty
import pydra  
from pydra import Workflow, mark, ShellCommandTask
from pydra.engine.specs import File
from pydra.tasks.mrtrix3.v3_0 import mrconvert, mrgrid, mrconvert, dwiextract, mrcalc, mrmath, dwibiasnormmask, mrthreshold
from pydra.tasks.fsl import epi_reg
from pydra.engine.specs import SpecInfo, BaseSpec, ShellSpec, ShellOutSpec
from fileformats.medimage import NiftiGzXBvec, NiftiGz
from fileformats.medimage_mrtrix3 import ImageFormat
from pathlib import Path

# Define the path and output_path variables
output_path = '/Users/arkievdsouza/git/ConnectomeBids_Pydrafied/outputs/carriage3/'
# alias mri_synthstrip="python /Users/arkievdsouza/synthstrip-docker"

@pydra.mark.task
def run_mri_synthstrip():
    import subprocess
    # Define the command to execute
    command = ["python", "/Users/arkievdsouza/synthstrip-docker"]
    # Execute the command
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Check if the command executed successfully
    if result.returncode != 0:
        # Print error message if the command failed
        print("Error running mri_synthstrip:")
        print(result.stderr.decode())
    # Return the stdout output
    return result.stdout.decode()

# Define the input_spec for the workflow
input_spec = {"dwi_preproc_mif": File, "FS_dir":str}
output_spec = {"dwi_processed_registered": File}

# Create a workflow 
wf = Workflow(name='connectomebids_carriage3_wf', input_spec=input_spec, cache_dir=output_path, output_spec=output_spec) 

# Step 4: Generate an image containing all voxels where the DWI contains valid data
# this step can be removed since the output is used in the iterative masking process (which is no long necessary)

# wf.add(
#     mrmath(
#         input=wf.lzin.dwi_preproc_mif,
#         output="dwi_mrmath_tmp.mif",
#         name="mrmath_max_task",
#         operation="max",
#         axis=3,

#     )
# )

# wf.add(
#     mrthreshold(
#         input=wf.mrmath_max_task.lzout.output,
#         output="dwi_validdata_image.mif",
#         name="mrthreshold_task",
#         abs=0.0,
#         axis=3,
#         comparison="gt"
        
#     )
# )

# REVISIT THIS Determine whether we are working with single-shell or multi-shell data
# wf.add(
#     mrinfo(
#         image=wf.lzin.dwi_preproc_mif,
#         name="mrinfo_bvals_task",
#         shell_bvalues=True,
#     )
# )

# Step 5: create mask. no need to re-write the iterative process that has been written in connectomebids - just use dwibiasnormmask (which does the same thing)
# mri_synthstrip is a hurdle. use dwi2mask in interim 
wf.add(
    dwibiasnormmask(
        input=wf.lzin.dwi_preproc_mif,
        name="dwibiasnormmask_task",
        output_dwi="dwi_biasnorm.mif",
        output_mask="dwi_mask.mif",
        mask_algo="threshold",
        output_bias="bias_field.mif", 
        output_tissuesum="tissue_sum.mif"      
    )
)

# Step 7: Crop images to reduce storage space (but leave some padding on the sides) - pointing to wrong folder, needs fix (nonurgent)
#grid DWI
wf.add(
    mrgrid(
        input=wf.dwibiasnormmask_task.lzout.output_dwi, 
        name="crop_task_dwi",
        operation="crop",
        output="dwi_crop.mif",
        mask=wf.dwibiasnormmask_task.lzout.output_mask,
        uniform=-3,
    )
)

#grid dwimask
wf.add(
    mrgrid(
        input=wf.dwibiasnormmask_task.lzout.output_mask, 
        name="crop_task_mask",
        operation="crop",
        output="mask_crop.mif",
        mask=wf.dwibiasnormmask_task.lzout.output_mask,
        uniform=-3,
    )
)

# REPLACE Step8-10 with epi_reg (and transform DWI to T1 space)

########################
# REGISTRATION CONTENT #
########################

# Step 8: Generate target images for T1->DWI registration

@mark.task
@mark.annotate({
    "FS_dir": str,
    "return": {
        "t1_FSpath": str,
        "t1brain_FSpath": str,
        "wmseg_FSpath": str,
        "normimg_FSpath": str,
        }
    })

def join_task(FS_dir: str, output_path: Path):
    t1_FSpath=os.path.join(FS_dir,"mri","T1.mgz")
    t1brain_FSpath=os.path.join(FS_dir,"mri","brainmask.mgz")
    wmseg_FSpath=os.path.join(FS_dir,"mri","wm.seg.mgz")
    normimg_FSpath=os.path.join(FS_dir,"mri","T1.mgz")

    return t1_FSpath, t1brain_FSpath, wmseg_FSpath, normimg_FSpath

wf.add(join_task(FS_dir=wf.lzin.FS_dir, name="join_task"))

# need to convert .mgz to nifti for registration
wf.add(
    mrconvert(
        input=wf.join_task.lzout.t1_FSpath,
        output="t1.nii.gz",
        name="nifti_t1",
    )
)

wf.add(
    mrconvert(
        input=wf.join_task.lzout.t1brain_FSpath,
        output="t1brain.nii.gz",
        name="nifti_t1brain",
    )
)

wf.add(
    mrconvert(
        input=wf.join_task.lzout.wmseg_FSpath,
        output="wmseg.nii.gz",
        name="nifti_wmseg",
    )
)

wf.add(
    mrconvert(
        input=wf.join_task.lzout.normimg_FSpath,
        output="normimg.nii.gz",
        name="nifti_normimg",
    )
)

#######################
# create meanb0 image #
#######################

wf.add(
    dwiextract(
        input=wf.dwibiasnormmask_task.output_dwi,
        output="bzero.mif",
        bzero=True,
        name="extract_bzeroes_task",
    )
)


# mrcalc spec info
mrcalc_max_input_spec = SpecInfo(
    name="Input",
    fields=[
    ( "image1", File,
      { "help_string": "path to input image 1",
        "argstr": "{image1}",
        "mandatory": True,
        "position": -4 } ),
    ( "number", str,
      { "help_string": "minimum value",
        "argstr": "{number}",
        "mandatory": True,
        "position": -3 } ),
    ( "operand", str,
      { "help_string": "operand to execute",
        "mandatory": True,
        "position": -2 ,
        "argstr": "-{operand}" }),
    ( "output_image", str,
      { "help_string": "path to output image",
        "output_file_template": "output_image.nii.gz",
        "argstr": "",
        "mandatory": True,
        "position": -1 } ),
    ( "datatype", str,
      { "help_string": "datatype option",
        "argstr": "-datatype {datatype}" ,
        "position": -5 } ),
    ],
    bases=(ShellSpec,) 
)

mrcalc_output_spec=SpecInfo(
    name="Output",
    fields=[
    ( "output_image", str,
      { "help_string": "path to output image",
        "mandatory": True,
        "position": -1 } ),
    ],
    bases=(ShellOutSpec,) 
)

# remove negative values from bzero volumes
wf.add(
    ShellCommandTask(
        name="mrcalc_max",
        executable="mrcalc",
        input_spec=mrcalc_max_input_spec, 
        output_spec=mrcalc_output_spec, 
        cache_dir=output_path,
        image1=wf.extract_bzeroes_task.lzout.output,
        number="0.0",
        operand='max',
        output_image='bzero_positive.mif'
    )
)

# create meanb0 image

wf.add(
    mrmath(
        input=wf.mrcalc_max.lzout.output_image,
        output="dwi_meanbzero.nii.gz",
        name="meanb0_task",
        operation="mean",
        axis=3,
    )
)

# Step 9: Perform DWI->T1 registration

wf.add(
    epi_reg(
        epi=wf.meanb0_task.lzout.output,
        t1_head=wf.nifti_t1.lzout.output,
        t1_brain=wf.nifti_t1brain.lzout.output,
        wmseg=wf.nifti_wmseg.lzout.output,
        out_base="dwi2T1_warp.nii.gz",
        name="epi_reg_task"
        
    )
)

# transformconvert task 
wf.add(
    transformconvert(

    )
)
# Step 10: Perform DWI->T1 transformation
# mrconvert

# wf.set_output(("carriage3_output", wf.dwibiasnormmask_task.lzout.output_dwi))
# wf.set_output(("carriage3_output", wf.crop_task_mask.lzout.output))
# wf.set_output(("carriage3_output", wf.crop_task_dwi.lzout.output))

wf.set_output(("carriage3_output", wf.epi_reg_task.lzout.out_base))

# ########################
# # Execute the workflow #
# ########################

# wf = connectomebids_carriage3_wf(direction=direction)
result = wf(dwi_preproc_mif="/Users/arkievdsouza/Desktop/ConnectomeBids/output/MRtrix3_connectome-preproc/sub-01/dwi/sub-01_desc-preproc_dwi.mif.gz",
    FS_dir="/Users/arkievdsouza/Desktop/ConnectomeBids/output/MRtrix3_connectome-participant_hcpmmp1/sub-01/scratch/freesurfer/",
    plugin="serial",
)
