// SAMPLE
this.manifest = {
    "name": "Uncensor ISP extension options",
    "icon": "icon.png",
    "settings": [
      {
        "tab": i18n.get("general"),
        "group": i18n.get("proxy_control"),
        "name": "proxy_control",
        "type": "radioButtons",
        "label": i18n.get('proxy_control_label'),
        "options": [
          [ 'use_auto', i18n.get('use_auto') ],
          [ 'never_use', i18n.get('never_use') ],
          [ 'ask_me', i18n.get('ask_me') ]
        ]
      },
      {
        "tab": i18n.get("general"),
        "group": i18n.get("notices"),
        "name": "proxy_active_message",
        "type": "checkbox",
        "label": i18n.get("proxy_active_message"),
      },
      {
        "tab": i18n.get("general"),
        "group": i18n.get("blocked_sites"),
        "name": "domains_description",
        "type": "description",
        "text": ""
      },
      {
        "tab": i18n.get("general"),
        "group": i18n.get("blocked_sites"),
        "name": "update_domains",
        "type": "button",
        "label": i18n.get('update_domains_label'),
        "text": i18n.get('update_domains_text')
      },
      {
        "tab": i18n.get("general"),
        "group": i18n.get("blocked_sites"),
        "name": "domains",
        "type": "comboTable",
        "heading1": i18n.get("domains"),
        "heading2": i18n.get("action"),
        "options":  [
          [ "use_global", i18n.get('use_global') ],
          [ "use_auto", i18n.get('use_auto') ],
          [ "never_use", i18n.get('never_use') ],
          [ "ask_me", i18n.get('ask_me') ]
        ]
      }

        // {
        //     "tab": i18n.get("general"),
        //     "group": i18n.get("facebook.com"),
        //     "name": "show_chat",
        //     "type": "checkbox",
        //     "label": i18n.get("show_chat"),
        // },
        // {
        //     "tab": i18n.get("general"),
        //     "group": i18n.get("facebook.com"),
        //     "name": "show_jewels",
        //     "type": "checkbox",
        //     "label": i18n.get("show_jewels"),
        // },
    ]
};
