#!/bin/bash
set -u

if [ ! -d tmp/ ]; then
  echo "Creating temporary directory for test output"
  mkdir tmp/
fi

echo "Generating PDF files for 2012-01 to 2012-12"

for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
  ./PyCalendarGen.py 2012 $month tmp/2012-${month}.pdf > tmp/2012-${month}.log &&\
  compare -metric AE tmp/2012-${month}.pdf testdata/2012-${month}.pdf png:- \
    > /dev/null 2> tmp/2012-${month}.log
  result=$?
  if [ "$result" -eq 0 ]; then
    metric=$(cat tmp/2012-${month}.log)
    if [ "$metric" -eq 0 ]; then
      echo -n "."
    else
      echo "F"
      echo "Files tmp/2012-${month}.pdf and testdata/2012-${month}.pdf don't match:"
      echo "$metric pixels differ in rendered output"
      exit 1
    fi
  else
    echo "E"
    echo "Error comparing files tmp/2012-${month}.pdf and testdata/2012-${month}.pdf:"
    cat tmp/2012-${month}.log
    exit $result
  fi
done
echo
