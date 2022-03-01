#!/bin/sh

DEST='/mnt/knot/www/NAKI_CPK/CPKSemanticEnrichment/inputs_czner_master/kb'
VERSION=`cat VERSION`

echo "Creating directory $DEST/$VERSION"
mkdir "$DEST/$VERSION"
echo "Copying files to $DEST/$VERSION"
cp VERSION HEAD-KB KBstatsMetrics.all "$DEST/$VERSION"
echo "Create symlink $DEST/new to $DEST/$VERSION"
( cd "$DEST" && ln --symbolic --relative --no-dereference --force "$VERSION" "new" )
