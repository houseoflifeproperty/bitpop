// Copyright 2012 the v8-i18n authors.
//
// Licensed under the Apache License, Version 2.0 (the 'License');
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an 'AS IS' BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Tests time zone support.

var df = Intl.DateTimeFormat();
assertEquals(getDefaultTimeZone(), df.resolvedOptions().timeZone);

// Short names (GMT, UTC) are case insensitive,
// but are upper case once they are resolved.
df = Intl.DateTimeFormat(undefined, {timeZone: 'UtC'});
assertEquals('UTC', df.resolvedOptions().timeZone);

df = Intl.DateTimeFormat(undefined, {timeZone: 'gmt'});
assertEquals('UTC', df.resolvedOptions().timeZone);

df = Intl.DateTimeFormat(undefined, {timeZone: 'America/Los_Angeles'});
assertEquals('America/Los_Angeles', df.resolvedOptions().timeZone);

df = Intl.DateTimeFormat(undefined, {timeZone: 'Europe/Belgrade'});
assertEquals('Europe/Belgrade', df.resolvedOptions().timeZone);

// This passes.
df = Intl.DateTimeFormat(undefined, {timeZone: 'GMT+07:00'});
assertEquals('GMT+07:00', df.resolvedOptions().timeZone);

// And this.
df = Intl.DateTimeFormat(undefined, {timeZone: 'GMT+0700'});
assertEquals('GMT+07:00', df.resolvedOptions().timeZone);

// Let's try negative offsets.
df = Intl.DateTimeFormat(undefined, {timeZone: 'GMT-05:00'});
assertEquals('GMT-05:00', df.resolvedOptions().timeZone);

// And this.
df = Intl.DateTimeFormat(undefined, {timeZone: 'GMT-0500'});
assertEquals('GMT-05:00', df.resolvedOptions().timeZone);

// Check Etc/XXX variants. They should work too.
df = Intl.DateTimeFormat(undefined, {timeZone: 'Etc/UTC'});
assertEquals('Etc/UTC', df.resolvedOptions().timeZone);

df = Intl.DateTimeFormat(undefined, {timeZone: 'Etc/GMT'});
assertEquals('Etc/GMT', df.resolvedOptions().timeZone);

df = Intl.DateTimeFormat(undefined, {timeZone: 'Etc/GMT+0'});
assertEquals('Etc/GMT+0', df.resolvedOptions().timeZone);

// This one should throw until we make ICU case insensitive.
assertThrows('Intl.DateTimeFormat(undefined, {timeZone: \'europe/belgrade\'})');

// Misspelled name should always throw.
assertThrows('Intl.DateTimeFormat(undefined, {timeZone: \'Aurope/Belgrade\'})');
