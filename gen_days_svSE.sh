#!/usr/bin/env bash
#
# Generate days_svSE.txt using https://api.dryg.net + some 'jq' magic (WIP)
#
curl https://api.dryg.net/dagar/v2.1/2018 |\
    jq -r '.dagar[] | ("\(.datum[8:10]).\(.datum[5:7]) ") + ("\(.namnsdag | join(" "))") + (if (.helgdag | length) > 0 then " / 1:\(.helgdag)" else "" end)'
