#!/usr/bin/env python3
"""Generate interferogram on AWS_BATCH.

This script executes the following steps:
    1) Sync interferogram processing directory from S3
    2) Download DEM, Orbit files, SLCs from ASF
    4) Run topsApp.py
    5) Upload results to S3
"""

import os
import argparse
import sys
import subprocess
import shutil

def cmdLineParse():
    """Command line parser."""
    parser = argparse.ArgumentParser(description='Run ISCE 2.3.2 topsApp')
    parser.add_argument('-i', type=str, dest='int_s3', required=True,
                        help='interferogram bucket name (s3://int-name)')
    parser.add_argument('-d', type=str, dest='dem_s3', required=True,
                        help='dem location (s3://dems-are-here)')


    return parser.parse_args()


def print_batch_params():
    """Print record of Docker container environment variables.

    print statements to stdout are recorded in AWS cloudwatch logs
    """
    print('CWD: ', os.getcwd())
    [print(x, os.environ[x]) for x in os.environ if x.startswith('AWS_BATCH')]


def run_bash_command(cmd):
    """Call a system command through the subprocess python module."""
    try:
        retcode = subprocess.call(cmd, shell=True)
        if retcode < 0:
            print("Child was terminated by signal", -retcode, file=sys.stderr)
        else:
            print("Child returned", retcode, file=sys.stderr)
    except OSError as e:
        print("Execution failed:", e, file=sys.stderr)


def get_proc_files(int_s3, dem_s3):
    """Download ISCE configuration files and DEM from S3."""
    cmds = [f'aws s3 sync {int_s3} .',
            f'aws s3 sync {dem_s3} .']
    for cmd in cmds:
        run_bash_command(cmd)


def download_slcs():
    """Download SLC images from ASF server."""
    cmd = 'aria2c -c -x 8 -s 8 -i download-links.txt'
    run_bash_command(cmd)

def cleanup():
    """Remove specified files from processing directory."""
    cmd = 'rm -r S1*zip dem* coarse_coreg coarse_interferogram coarse_offsets \
    ESD fine_coreg fine_interferogram fine_offsets \
    geom_master masterdir PICKLE slavedir'
    #cmd = 'rm -r S1*zip dem*'
    run_bash_command(cmd)
    #

def run_isce():
    """Call topsApp.py to generate single interferogram."""
    cmd = 'topsApp.py --steps 2>&1 | tee topsApp.log'
    print(cmd)
    run_bash_command(cmd)


def main():
    """Process single interferogram."""
    inps = cmdLineParse()
    print_batch_params()
    intname = inps.int_s3.lstrip('s3://')
    if not os.path.isdir(intname): os.makedirs(intname)
    os.chdir(intname)

    get_proc_files(inps.int_s3, inps.dem_s3)
    download_slcs()
    run_isce()
    # Not really necessary since EBS drive deleted
    #cleanup()


if __name__ == '__main__':
    main()
