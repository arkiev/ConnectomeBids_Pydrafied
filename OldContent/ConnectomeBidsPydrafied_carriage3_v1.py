from ast import alias
import os
import typing as ty
import pydra  
from pydra import Workflow, mark, ShellCommandTask
from pydra.engine.specs import File
from pydra.tasks.mrtrix3.v3_0 import TransformConvert,MrTransform, MrConvert, MrGrid, DwiExtract, MrCalc, MrMath, DwiBiasnormmask, MrThreshold
from pydra.tasks.fsl.auto  import EpiReg
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
input_spec = {"dwi_preproc_mif": File, "FS_dir":str} #, "bzero_positive": File, "mean_bzero":File}
# output_spec = {"warp": File}

# Create a workflow 
wf = Workflow(name='connectomebids_carriage3_wf', input_spec=input_spec, cache_dir=output_path,)# output_spec=output_spec) 

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
# wf.add(
#     dwibiasnormmask(
#         input=wf.lzin.dwi_preproc_mif,
#         name="dwibiasnormmask_task",
#         output_dwi="dwi_biasnorm.mif",
#         output_mask="dwi_mask.mif",
#         mask_algo="threshold",
#         output_bias="bias_field.mif", 
#         output_tissuesum="tissue_sum.mif"      
#     )
# )

# Step 7: Crop images to reduce storage space (but leave some padding on the sides) - pointing to wrong folder, needs fix (nonurgent)
#grid DWI
# wf.add(
#     mrgrid(
#         input=wf.dwibiasnormmask_task.lzout.output_dwi, 
#         name="crop_task_dwi",
#         operation="crop",
#         output="dwi_crop.mif",
#         mask=wf.dwibiasnormmask_task.lzout.output_mask,
#         uniform=-3,
#     )
# )

# #grid dwimask
# wf.add(
#     mrgrid(
#         input=wf.dwibiasnormmask_task.lzout.output_mask, 
#         name="crop_task_mask",
#         operation="crop",
#         output="mask_crop.mif",
#         mask=wf.dwibiasnormmask_task.lzout.output_mask,
#         uniform=-3,
#     )
# )

# # REPLACE Step8-10 with epi_reg (and transform DWI to T1 space)

# ########################
# # REGISTRATION CONTENT #
# ########################

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
    MrConvert(
        in_file=wf.join_task.lzout.t1_FSpath,
        out_file="t1.nii.gz",
        name="nifti_t1",
    )
)

wf.add(
    MrConvert(
        in_file=wf.join_task.lzout.t1brain_FSpath,
        out_file="t1brain.nii.gz",
        name="nifti_t1brain",
    )
)

wf.add(
    MrConvert(
        in_file=wf.join_task.lzout.wmseg_FSpath,
        out_file="wmseg.nii.gz",
        name="nifti_wmseg",
    )
)

wf.add(
    MrConvert(
        in_file=wf.join_task.lzout.normimg_FSpath,
        out_file="normimg.nii.gz",
        name="nifti_normimg",
    )
)

# extract meanb0 volumes #

wf.add(
    DwiExtract(
        # input=wf.dwibiasnormmask_task.lzout.output_dwi,
        in_file=wf.lzin.dwi_preproc_mif,
        out_file="bzero.mif",
        bzero=True,
        name="extract_bzeroes_task",
    )
)

# mrcalc spec info
mrcalc_max_input_spec = SpecInfo(
    name="Input",
    fields=[
    ( "image1", str,
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
        # "mandatory": True,
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
        "mandatory": False,
        "output_file_template": "out_file.mif",
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
        # cache_dir=output_path,
        image1=wf.extract_bzeroes_task.lzout.out_file,
        number="0.0",
        operand='max',
        # output_image='bzero_positive.mif'
    )
)

# create meanb0 image
wf.add(
    MrMath(
        in_file=wf.mrcalc_max.lzout.output_image,
        out_file="dwi_meanbzero.nii.gz",
        name="meanb0_task",
        operation="mean",
        axis=3,
    )
)

# make wm mask a binary image
wf.add(
    ShellCommandTask(
        name="mrcalc_wmbin",
        executable="mrcalc",
        input_spec=mrcalc_max_input_spec, 
        output_spec=mrcalc_output_spec, 
        cache_dir=output_path,
        image1=wf.nifti_wmseg.lzout.out_file,
        number="0",
        operand='gt',
        # output_image='wmseg_binary.mif'
    )
)

# Step 9: Perform DWI->T1 registration
wf.add(
    EpiReg(
        epi=wf.meanb0_task.lzout.out_file,
        t1_head=wf.nifti_normimg.lzout.out_file,
        t1_brain=wf.nifti_t1brain.lzout.out_file,
        wmseg=wf.mrcalc_wmbin.lzout.output_image,
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
        flirt_in=wf.meanb0_task.lzout.out_file,
        flirt_ref=wf.nifti_t1brain.lzout.out_file,
        out_file="epi2struct_mrtrix.txt",
        name="transformconvert_task", 

    )
)

# Step 10: Apply transform (to get DWI in T1 space)
wf.add(
    MrTransform(
        name="transformT1_task",
        in_file=wf.lzin.dwi_preproc_mif,
        inverse=False,
        out_file="DWI_registered.mif",
        linear=wf.transformconvert_task.lzout.out_file,
        strides=wf.nifti_t1brain.lzout.out_file,
    )

)


# SET WF OUTPUT
wf.set_output(("carriage3_output", wf.transformT1_task.lzout.out_file))

# ########################
# # Execute the workflow #
# ########################

result = wf(
    dwi_preproc_mif="/Users/arkievdsouza/git/ConnectomeBids_Pydrafied/outputs/carriage3/dwi_biasnorm.mif",
    FS_dir="/Users/arkievdsouza/Desktop/ConnectomeBids/output/MRtrix3_connectome-participant_hcpmmp1/sub-01/scratch/freesurfer/",
    plugin="serial",
)
