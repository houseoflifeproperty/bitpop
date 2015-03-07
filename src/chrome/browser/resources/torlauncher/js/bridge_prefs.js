var torlauncher = torlauncher || {};

torlauncher.registerBridgePrefs = function *() {
  yield torlauncher.util.setPref("defaultBridgeRecommendedType", "obfs3");

  var defaultBridge = {
    "obfs3": [
      "obfs3 83.212.101.3:80 A09D536DD1752D542E1FBB3C9CE4449D51298239",
      "obfs3 169.229.59.74:31493 AF9F66B7B04F8FF6F32D455F05135250A16543C9",
      "obfs3 169.229.59.75:46328 AF9F66B7B04F8FF6F32D455F05135250A16543C9",
      "obfs3 109.105.109.163:38980 1E05F577A0EC0213F971D81BF4D86A9E4E8229ED",
      "obfs3 109.105.109.163:47779 4C331FA9B3D1D6D8FB0D8FBBF0C259C360D97E6A"
    ],
    "meek-amazon": [
      "meek 0.0.2.0:2 url=https://d2zfqthxsdq309.cloudfront.net/ front=a0.awsstatic.com"
    ],
    "fte-ipv6": [
      "fte [2001:49f0:d002:1::2]:80 B629B0B607C8AC9349B5646C24E9D242184F5B6E",
      "fte [2001:49f0:d00a:1::c]:80 2BD466989944867075E872310EBAD65BC88C8AEF"
    ],
    "meek-azure": [
      "meek 0.0.2.0:3 url=https://az668014.vo.msecnd.net/ front=ajax.aspnetcdn.com"
    ],
    "flashproxy": [
      "flashproxy 0.0.1.0:1",
      "flashproxy 0.0.1.0:2",
      "flashproxy 0.0.1.0:3",
      "flashproxy 0.0.1.0:4",
      "flashproxy 0.0.1.0:5"
    ],
    "meek-google": [
      "meek 0.0.2.0:1 url=https://meek-reflect.appspot.com/ front=www.google.com"
    ],
    "fte": [
      "fte 192.240.101.106:80 B629B0B607C8AC9349B5646C24E9D242184F5B6E",
      "fte 50.7.176.114:80 2BD466989944867075E872310EBAD65BC88C8AEF",
      "fte 131.252.210.150:8080 0E858AC201BF0F3FA3C462F64844CBFFC7297A42",
      "fte 128.105.214.161:8080 1E326AAFB3FCB515015250D8FCCC8E37F91A153B",
      "fte 128.105.214.162:8080 FC562097E1951DCC41B7D7F324D88157119BB56D",
      "fte 128.105.214.163:8080 A17A40775FBD2CA1184BF80BFC330A77ECF9D0E9"
    ],
    "scramblesuit": [
      "scramblesuit 188.226.213.208:54278 AA5A86C1490296EF4FACA946CC5A182FCD1C5B1E password=MD2VRP7WXAMSG7MKIGMHI4CB4BMSNO7T",
      "scramblesuit 83.212.101.3:443 A09D536DD1752D542E1FBB3C9CE4449D51298239 password=XTCXLG2JAMJKZW2POLBAOWOQETQSMASH"
    ]
  };
  yield torlauncher.util.setPref("defaultBridge", defaultBridge);
};
