#!/bin/bash

SRC_DIR=$1
DEST_DIR=$2

scp -r $SRC_DIR/* $DEST_DIR
