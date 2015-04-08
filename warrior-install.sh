#!/bin/sh -e

VERSION='1.0'
TARBALL='wpull-1.0-linux-i686-3.4.3-20150314005854.zip'
CHECKSUM=9bb26c21e4904c92d530455646365d0f
DOWNLOAD_URL="https://launchpad.net/wpull/trunk/v${VERSION}/+download/${TARBALL}"
INSTALL_DIR="${HOME}/.local/share/wpull-${VERSION}/"

if [ ! -e "${INSTALL_DIR}/wpull" ]; then
    echo "Downloading Wpull"
    wget $DOWNLOAD_URL --continue --directory-prefix /tmp/

    echo "Verify checksum"
    RESULT_CHECKSUM=`md5sum "/tmp/${TARBALL}" | cut -f 1 -d " "`
    if [ "$RESULT_CHECKSUM" != "$CHECKSUM" ]; then
        echo "Checksum failed. Got ${RESULT_CHECKSUM}. Need ${CHECKSUM}"
        exit 1
    fi

    echo "Extracting contents to ${INSTALL_DIR}"
    mkdir -p "${INSTALL_DIR}"
    # tar -xzf "/tmp/${TARBALL}" --strip-components 1 --directory "${INSTALL_DIR}"
    python -c "import zipfile; f=zipfile.ZipFile('/tmp/${TARBALL}'); f.extractall('${INSTALL_DIR}')"
    chmod +x ${INSTALL_DIR}/wpull

    echo Done
fi
