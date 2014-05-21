solutions = [
  { "name"        : "25.0.1364.72",
    "url"         : "https://src.chromium.org/chrome/releases/25.0.1364.72",
    "deps_file"   : "DEPS",
    "managed"     : True,
    "custom_deps" : {
 		"build/third_party/gsutil" : None,
        "src/third_party/WebKit/LayoutTests": None,
        "src/chrome_frame/tools/test/reference_build/chrome": None,
        "src/chrome_frame/tools/test/reference_build/chrome_win": None,
        "src/chrome/tools/test/reference_build/chrome": None,
        "src/chrome/tools/test/reference_build/chrome_linux": None,
        "src/chrome/tools/test/reference_build/chrome_mac": None,
        "src/chrome/tools/test/reference_build/chrome_win": None,
        "src/third_party/hunspell_dictionaries": None,
        "src/third_party/gles2_book": None,  
    },
    "custom_vars" : {
        "jsoncpp": "http://svn.code.sf.net/p/jsoncpp/code",
    },
    "safesync_url": "",
  },
]
