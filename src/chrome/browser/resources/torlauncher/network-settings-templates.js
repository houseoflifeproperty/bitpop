// BitPop browser. Tor launcher integration part.
// Copyright (C) 2014 BitPop AS
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

var torlauncher = torlauncher || {};

torlauncher.ns_templates = {
  "proxy_settings": [
    '<section class="nw-proxy-settings-question nw-question" hidden>',
      '<p i18n="torSettings.enterProxy"></p>',
      '<form class="proxy-settings-form rounded-rect-highlight">',
        '<div class="settings-row">',
          '<label i18n="torsettings.useProxy.type"></label>',
          '<div class="table-cell">',
            '<select id="ps_proxy_type">',
              '<option value="">-</option>',
              '<option value="socks4">SOCKS 4</option>',
              '<option value="socks5">SOCKS 5</option>',
              '<option value="http_s">HTTP / HTTPS</option>',
            '</select>',
          '</div>',
        '</div>',
        '<div class="settings-row">',
          '<label i18n="torsettings.useProxy.address"></label>',
          '<div class="table-cell">',
            '<input type="text" id="ps_address" i18n_placeholder="torsettings.useProxy.address.placeholder" />',
            '<div class="port-section">',
              '<label i18n="torsettings.useProxy.port"></label>',
              '<input type="text" id="ps_port" />',
            '</div>',
          '</div>',
        '</div>',
        '<div class="settings-row userpass-row">',
          '<label i18n="torsettings.useProxy.username"></label>',
          '<div class="table-cell">',
            '<input type="text" id="ps_username" i18n_placeholder="torsettings.optional" />',
            '<div class="pass-section">',
              '<label i18n="torsettings.useProxy.password"></label>',
              '<input type="password" id="ps_password" i18n_placeholder="torsettings.optional" />',
            '</div>',
          '</div>',
        '</div>',
      '</form>',
    '</section>'
  ].join("\n"),

  "bridges_settings": [
    '<section class="nw-configure-bridges nw-question" hidden>',
      '<header id="nw_configure_bridges_header" hidden>',
        '<h1 i18n="torSettings.bridgeSettingsPrompt" class="question-head"></h1>',
      '</header>',
      '<form class="bridges-config-form rounded-rect-highlight">',
        '<label class="bc-radio-label" for="with_provided_bridges" i18n="torsettings.useBridges.default"></label>',
        '<input id="with_provided_bridges" type="radio" name="bridges_type" value="provided" checked />',
        '<div class="bridges-radio-subitem br-subitem-1">',
          '<label i18n="torsettings.useBridges.type"></label>',
          '<select id="bc_transport_type">',
            '<option value="flashproxy">flashproxy</option>',
            '<option value="fte">fte</option>',
            '<option value="fte-ipv6">fte-ipv6</option>',
            '<option value="meek-amazon">meek-amazon</option>',
            '<option value="meek-azure">meek-azure</option>',
            '<option value="meek-google">meek-google</option>',
            '<option value="obfs3" selected>obfs3 (recommended)</option>',
            '<option value="scramblesuit">scramblesuit</option>',
          '</select>',
        '</div>',
        '<label class="bc-radio-label" for="with_custom_bridges" i18n="torsettings.useBridges.custom"></label>',
        '<input id="with_custom_bridges" type="radio" name="bridges_type" value="custom" />',
        '<div class="bridges-radio-subitem br-subitem-2">',
          '<label i18n="torsettings.useBridges.label"></label>',
          '<div><textarea id="bc_custom_bridges" i18n_placeholder="torsettings.useBridges.placeholder"></textarea></div>',
        '</div>',
      '</form>',
    '</section>'
  ].join("\n"),

  "firewall_settings": [
    '<section class="nw-firewall-settings nw-question" hidden>',
      '<form class="firewall-settings-form rounded-rect-highlight">',
        '<label i18n="torsettings.firewall.allowedPorts"></label>',
        '<input type="text" id="fs_allowed_ports" value="80,443" />',
      '</form>',
    '</section>'
  ].join("\n")
};
