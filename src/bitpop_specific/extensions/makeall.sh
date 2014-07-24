# BitPop browser. Build system.
# Copyright (C) 2014 BitPop AS
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

WD=`pwd`
BASE_DIR=`dirname $0`
EXT_DIR="../../chrome/browser/extensions/default_extensions"
EXT_DEFS="$EXT_DIR/external_extensions.json"
UPLOAD_DIR="./upload"
BASE_URL="https://tools.bitpop.com/ext"
UPDATES_XML_PATH="$UPLOAD_DIR/updates.xml"
PRODVERSIONMIN_PATH="./prodversionmin.csv"

# extension names list
EXT_NAMES="dropdown_most_visited facebook_friends facebook_messages facebook_notifications uncensor_domains uncensor_proxy share_this"

make_app_entry() {
  # $1 - extension id,
  # $2 - extension version
  # $3 - extension filename (without extension and version suffix)

  LAST_APP_ENTRY="<app appid='$1'>"
  while read line
  do
    IFS=, read id ext_ver min_prod_ver junk_ < <(echo "$line")
    if [ "$id" == "$1" ]; then

      if [ "$ext_ver" == "-" ]; then
        ext_ver="$2"
      fi

      LAST_APP_ENTRY=$LAST_APP_ENTRY"\n  <updatecheck codebase='$BASE_URL/$3-$ext_ver.crx' version='$ext_ver' prodversionmin='$min_prod_ver'/>"
    fi
  done < <(awk 'NR > 1' "$PRODVERSIONMIN_PATH")

  LAST_APP_ENTRY=$LAST_APP_ENTRY"\n</app>"

  return 0
}

echo "=== Started ==="
echo

cd "$BASE_DIR"
[ -d "$UPLOAD_DIR" ] || mkdir "$UPLOAD_DIR"
echo -e "<?xml version='1.0' encoding='UTF-8'?>\n<gupdate xmlns='http://www.google.com/update2/response' protocol='2.0'>" > "$UPDATES_XML_PATH"

find . -name "*.swl" -o -name "*.swm" -o -name "*.swn" -o -name "*.swo" -o -name "*.swp" -o -name "*.un~" -o -name ".DS_Store" | xargs rm -f

echo "// This json file will contain a list of extensions that will be included" > "$EXT_DEFS"
echo "// in the installer." >> "$EXT_DEFS"
echo "" >> "$EXT_DEFS"
echo "{" >> "$EXT_DEFS"

for EXT in $EXT_NAMES; do
  echo "=== Processing $EXT ..."

  ./crxmake.sh "$EXT/" "$EXT.pem"
  cp -f "$EXT.crx" "$EXT_DIR/"

  EXT_ID=`cat "$EXT.pem" | openssl rsa -pubout -outform DER | openssl dgst -sha256 | cut -c 1-32 | tr '0-9a-f' 'a-p'`
  #EXT_ID=$($EXT_ID_COMMAND)
  EXT_VERSION=`grep \"version\": "$EXT/manifest.json" | sed -E 's/[^[:digit:]\.]//g'`

#  echo "  \"$EXT_ID\": {" >> "$EXT_DEFS"
#  echo "    \"external_crx\": \"$EXT.crx\"," >> "$EXT_DEFS"
#  echo "    \"external_version\": \"$EXT_VERSION\"" >> "$EXT_DEFS"
#  echo "  }," >> "$EXT_DEFS"

  cp -f "$EXT.crx" "$UPLOAD_DIR/$EXT-$EXT_VERSION.crx"

  make_app_entry $EXT_ID $EXT_VERSION $EXT
  echo -e "$LAST_APP_ENTRY" >> "$UPDATES_XML_PATH"

  echo "... Done ==="
done

#echo "  \"nnbmlagghjjcbdhgmkedmbmedengocbn\": {" >> "$EXT_DEFS"
#echo "    \"external_update_url\": \"http://clients2.google.com/service/update2/crx\"" >> "$EXT_DEFS"
#echo "  }," >> "$EXT_DEFS"
#if [ "$1" == "-i" ]; then
#  echo "  \"kggkfhmkfhphhpieneonpjdggjheibjg\": {" >> "$EXT_DEFS"
#  echo "    \"external_update_url\": \"http://tools.bitpop.com/ext/update.xml\"" >> "$EXT_DEFS"
#  echo "  }," >> "$EXT_DEFS"
#fi
#echo "  \"geoplninmkljnhklaihoejihlogghapi\": {" >> "$EXT_DEFS"
#echo "    \"external_crx\": \"share_button.crx\"," >> "$EXT_DEFS"
#echo "    \"external_version\": \"0.4\"" >> "$EXT_DEFS"
#echo "  }" >> "$EXT_DEFS"
#echo "}" >> "$EXT_DEFS"

echo "</gupdate>" >> "$UPDATES_XML_PATH"

cd "$WD"

echo
echo "=== Finished ==="

