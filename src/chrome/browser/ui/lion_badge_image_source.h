// BitPop browser with features like Facebook chat and uncensored browsing. 
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

#ifndef CHROME_BROWSER_UI_LION_BADGE_IMAGE_SOURCE_H_
#define CHROME_BROWSER_UI_LION_BADGE_IMAGE_SOURCE_H_

#include <string>

#include "extensions/common/extension.h"
#include "ui/gfx/image/canvas_image_source.h"
#include "ui/gfx/image/image_skia.h"

namespace gfx {
class Size;
}

// CanvasImageSource for creating a badge.
class LionBadgeImageSource
    : public gfx::CanvasImageSource {
 public:
  LionBadgeImageSource(const gfx::Size& icon_size,
                       const std::string& text);
  virtual ~LionBadgeImageSource();

 private:
  static int actual_width(const gfx::Size& icon_size,
                          const std::string& text);

  virtual void Draw(gfx::Canvas* canvas) OVERRIDE;

    // Text to be displayed on the badge.
  std::string text_;
  gfx::Size icon_size_;

  DISALLOW_COPY_AND_ASSIGN(LionBadgeImageSource);
};

#endif  // CHROME_BROWSER_UI_LION_BADGE_IMAGE_SOURCE_H_
