#!/bin/bash -e

export LOG_DIR=/var/log/kolla/vmware_collector

if [[ ! -d ${LOG_DIR} ]]; then
    mkdir -p ${LOG_DIR}
fi

if [[ $(stat -c %a ${LOG_DIR}) != "755" ]]; then
    chmod 755 ${LOG_DIR}
fi

if [[ "${!KOLLA_BOOTSTRAP[@]}" ]]; then
    vmware-collector-upgrade --config-file /etc/vmware_collector/vmware_collector.conf
    exit 0
fi
