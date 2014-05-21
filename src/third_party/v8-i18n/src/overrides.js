// Copyright 2012 the v8-i18n authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// ECMAScript 402 API implementation is broken into separate files for
// each service. The build system combines them together into one
// Intl namespace.


// Save references to Intl objects and methods we use, for added security.
var collator = Intl.Collator;
var numberFormat = Intl.NumberFormat;
var dateFormat = Intl.DateTimeFormat;


/**
 * Compares this and that, and returns less than 0, 0 or greater than 0 value.
 * Overrides the built-in method.
 */
Object.defineProperty(String.prototype, 'localeCompare', {
  value: function(that, locales, options) {
    // Call internal method.
    return compare(new collator(locales, options), this, that);
  },
  writable: true,
  configurable: true,
  enumerable: false
});


/**
 * Formats a Number object (this) using locale and options values.
 * If locale or options are omitted, defaults are used.
 */
Object.defineProperty(Number.prototype, 'toLocaleString', {
  value: function(locales, options) {
    // Call internal method.
    return formatNumber(new numberFormat(locales, options), this);
  },
  writable: true,
  configurable: true,
  enumerable: false
});


/**
 * Returns actual formatted date.
 */
function toLocaleDateTime(date, locales, options, required, defaults) {
  if (!(date instanceof Date)) {
    throw new TypeError('Method invoked on an object that is not Date.');
  }

  if (isNaN(date)) {
    return 'Invalid Date';
  }

  var internalOptions = toDateTimeOptions(options, required, defaults);
  // Call internal method.
  return formatDate(new dateFormat(locales, internalOptions), date);
}


/**
 * Formats a Date object (this) using locale and options values.
 * If locale or options are omitted, defaults are used - both date and time are
 * present in the output.
 */
Object.defineProperty(Date.prototype, 'toLocaleString', {
  value: function(locales, options) {
    return toLocaleDateTime(this, locales, options, 'any', 'all');
  },
  writable: true,
  configurable: true,
  enumerable: false
});


/**
 * Formats a Date object (this) using locale and options values.
 * If locale or options are omitted, defaults are used - only date is present
 * in the output.
 */
Object.defineProperty(Date.prototype, 'toLocaleDateString', {
  value: function(locales, options) {
    return toLocaleDateTime(this, locales, options, 'date', 'date');
  },
  writable: true,
  configurable: true,
  enumerable: false
});


/**
 * Formats a Date object (this) using locale and options values.
 * If locale or options are omitted, defaults are used - only time is present
 * in the output.
 */
Object.defineProperty(Date.prototype, 'toLocaleTimeString', {
  value: function(locales, options) {
    return toLocaleDateTime(this, locales, options, 'time', 'time');
  },
  writable: true,
  configurable: true,
  enumerable: false
});
