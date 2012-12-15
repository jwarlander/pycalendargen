#!/bin/bash
set -u

if [ ! -d tmp/ ]; then
  echo "Creating temporary directory for test output"
  mkdir tmp/
fi

echo "Generating PDF files for 2012-01 to 2012-12"

for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
  ./PyCalendarGen.py 2012 $month tmp/2012-${month}.pdf > tmp/2012-${month}.log &&\
  comparepdf -c a -v 1 tmp/2012-${month}.pdf testdata/2012-${month}.pdf
  result=$?
  if [ "$result" -eq 0 ]; then
    echo -n "."
  else
    echo "* Error while verifying 2012-${month}.pdf"
    exit $result
  fi
done
echo
