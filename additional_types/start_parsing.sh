#!/bin/bash

#Autor: xreset00 (René Rešetár) private: renco.resetar@gmail.com, school: xreset00@fit.vutbr.cz
#Project: Vytvoření znalostní báze entit z české Wikipedie (shortcut: entity_kb_czech9)

export LC_ALL="C.UTF-8"

#default values
LOG=false
DUMP_PATH="/mnt/minerva1/nlp/datasets/wikipedia/wikidata-20200727/wikidata-20200720-all.json"

# saved values
LAUNCHED=$0

usage()
{
    echo "Usage: start_parsing.sh [PARAMETERS]"
    echo ""
    echo -e "  -h, --help   show this help message and exit"
    echo ""
    echo -e "OPTIONAL arguments:"
    echo -e "  -d <dump> path of dump to process (default: ${DUMP_PATH})"
    echo -e "  -u [<login>] upload (deploy) KB to webstorage via given login"
    echo -e "               (default current user)"
    echo -e "  --log        log to start.sh.stdout, start.sh.stderr and start.sh.stdmix"
    echo ""
}

DEPLOY=false

while [ "$1" != "" ]; do
    PARAM=`echo $1 | awk -F= '{print $1}'`
    VALUE=`echo $1 | awk -F= '{print $2}'`
    case $PARAM in
        -h | --help)
            usage
            exit
            ;;
        -d)
            DUMP_PATH=$2
            shift
            ;;
        -u)
            DEPLOY=true
            LOGIN=$2
            if test "${LOGIN:0:1}" = "-"
            then
                DEPLOY_USER=`whoami`
            else
                DEPLOY_USER=$2
                shift
            fi
            ;;
        --log)
            LOG=true
            ;;
        *)
            >&2 echo "ERROR: unknown parameter \"$PARAM\""
            usage
            exit 1
            ;;
    esac
    shift
done

# change of directory to the one that start_parsing.sh was called from
cd `dirname "${LAUNCHED}"`

# Test file existence and zero-length of file
#if test ! -s "${DUMP_PATH}" -o ! -r "${DUMP_PATH}"
#then
#    >&2 echo "ERROR: wikipedia pages dump file does not exist or is zero-length"
#    exit 2
#fi

if $LOG; then
	rm -f start.sh.fifo.stdout start.sh.fifo.stderr start.sh.fifo.stdmix
	mkfifo start.sh.fifo.stdout start.sh.fifo.stderr start.sh.fifo.stdmix

	cat start.sh.fifo.stdout | tee start.sh.stdout > start.sh.fifo.stdmix &
	cat start.sh.fifo.stderr | tee start.sh.stderr > start.sh.fifo.stdmix &
	cat start.sh.fifo.stdmix > start.sh.stdmix &
	exec > start.sh.fifo.stdout 2> start.sh.fifo.stderr
fi

DUMP_DIR=`dirname "${DUMP_PATH}"`

# If Wikipedia dump path is symlink, then read real path
if test -L "${DUMP_PATH}"
then
    DUMP_PATH=`readlink "${DUMP_PATH}"`
    if test `dirname "${DUMP_PATH}"` = "."
    then
      DUMP_PATH="${DUMP_DIR}/${DUMP_PATH}"
    fi
fi

# Run wikidata json dump extractor to create new KB
CMD="python3 $PWD/ent_parser.py --dump \"${DUMP_PATH}\" --final 2>entities_processing.log"
echo "RUNNING COMMAND: ${CMD}"
eval $CMD

# Run script to download images
CMD="python3 $PWD/download_images.py"
echo "RUNNING COMMAND: ${CMD}"
eval $CMD

# Add metrics to newly created KB
if $LOG
then
    metrics_params="--log"
fi
./metrics/start.sh ${metrics_params}

#TODO
#if $DEPLOY
#then
#    ./deploy.sh -u $DEPLOY_USER
#fi