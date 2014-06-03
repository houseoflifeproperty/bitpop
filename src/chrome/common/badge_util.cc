// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "chrome/common/badge_util.h"

#include "base/logging.h"
#include "base/utf_string_conversions.h"
#include "grit/ui_resources.h"
#include "third_party/skia/include/core/SkPaint.h"
#include "third_party/skia/include/core/SkTypeface.h"
#include "third_party/skia/include/effects/SkBlurDrawLooper.h"
#include "third_party/skia/include/effects/SkGradientShader.h"
#include "ui/base/resource/resource_bundle.h"
#include "ui/gfx/canvas.h"
#include "ui/gfx/font.h"
#include "ui/gfx/rect.h"
#include "ui/gfx/size.h"
#include "ui/gfx/skia_util.h"

namespace {

// Different platforms need slightly different constants to look good.
#if defined(OS_LINUX) && !defined(TOOLKIT_VIEWS)
const float kTextSize = 9.0;
const int kBottomMarginBrowserAction = 0;
const int kBottomMarginPageAction = 2;
const int kPadding = 2;
const int kTopTextPadding = 0;
#elif defined(OS_LINUX) && defined(TOOLKIT_VIEWS)
const float kTextSize = 8.0;
const int kBottomMarginBrowserAction = 5;
const int kBottomMarginPageAction = 2;
const int kPadding = 2;
const int kTopTextPadding = 1;
#elif defined(OS_MACOSX)
const float kTextSize = 9.0;
const int kBottomMarginBrowserAction = 5;
const int kBottomMarginPageAction = 2;
const int kPadding = 4;
const int kTopTextPadding = 0;
#else
const float kTextSize = 10;
const int kBottomMarginBrowserAction = 5;
const int kBottomMarginPageAction = 2;
const int kPadding = 2;
// The padding between the top of the badge and the top of the text.
const int kTopTextPadding = -1;
#endif

const int kBadgeHeight = 15;
const int kMaxTextWidth = 23;

// The minimum width for center-aligning the badge.
const int kCenterAlignThreshold = 20;

}  // namespace

namespace badge_util {

SkPaint* GetBadgeTextPaintSingleton() {
#if defined(OS_MACOSX)
  const char kPreferredTypeface[] = "Helvetica Bold";
#else
  const char kPreferredTypeface[] = "Arial";
#endif

  static SkPaint* text_paint = NULL;
  if (!text_paint) {
    text_paint = new SkPaint;
    text_paint->setAntiAlias(true);
    text_paint->setTextAlign(SkPaint::kLeft_Align);

    skia::RefPtr<SkTypeface> typeface = skia::AdoptRef(
        SkTypeface::CreateFromName(kPreferredTypeface, SkTypeface::kBold));
    // Skia doesn't do any font fallback---if the user is missing the font then
    // typeface will be NULL. If we don't do manual fallback then we'll crash.
    if (typeface) {
      text_paint->setFakeBoldText(true);
    } else {
      // Fall back to the system font. We don't bold it because we aren't sure
      // how it will look.
      // For the most part this code path will only be hit on Linux systems
      // that don't have Arial.
      ResourceBundle& rb = ResourceBundle::GetSharedInstance();
      const gfx::Font& base_font = rb.GetFont(ResourceBundle::BaseFont);
      typeface = skia::AdoptRef(SkTypeface::CreateFromName(
          base_font.GetFontName().c_str(), SkTypeface::kNormal));
      DCHECK(typeface);
    }

    text_paint->setTypeface(typeface.get());
    // |text_paint| adds its own ref. Release the ref from CreateFontName.
  }
  return text_paint;
}

SkBitmap DrawBadgeIconOverlay(const SkBitmap& icon,
                              float font_size,
                              const string16& text,
                              const string16& fallback) {
  const int kMinPadding = 1;

  // Calculate the proper style/text overlay to render on the badge.
  SkPaint* paint = badge_util::GetBadgeTextPaintSingleton();
  paint->setTextSize(SkFloatToScalar(font_size));
  paint->setColor(SK_ColorWHITE);

  std::string badge_text = UTF16ToUTF8(text);

  // See if the text will fit - otherwise use a default.
  SkScalar text_width = paint->measureText(badge_text.c_str(),
                                           badge_text.size());

  if (SkScalarRound(text_width) > (icon.width() - kMinPadding * 2)) {
    // String is too large - use the alternate text.
    badge_text = UTF16ToUTF8(fallback);
    text_width = paint->measureText(badge_text.c_str(), badge_text.size());
  }

  // When centering the text, we need to make sure there are an equal number
  // of pixels on each side as otherwise the text looks off-center. So if the
  // padding would be uneven, clip one pixel off the right side.
  int badge_width = icon.width();
  if ((SkScalarRound(text_width) % 1) != (badge_width % 1))
    badge_width--;

  // Render the badge bitmap and overlay into a canvas.
  scoped_ptr<gfx::Canvas> canvas(new gfx::Canvas(
      gfx::Size(badge_width, icon.height()), ui::SCALE_FACTOR_100P, false));
  canvas->DrawImageInt(gfx::ImageSkia(icon), 0, 0);

  // Draw the text overlay centered horizontally and vertically. Skia expects
  // us to specify the lower left coordinate of the text box, which is why we
  // add 'font_size - 1' to the height.
  SkScalar x = (badge_width - text_width)/2;
  SkScalar y = (icon.height() - font_size)/2 + font_size - 1;
  canvas->sk_canvas()->drawText(
      badge_text.c_str(), badge_text.size(), x, y, *paint);

  // Return the generated image.
  return canvas->ExtractImageRep().sk_bitmap();
}

// Get badge rect
// Code repetition
gfx::Rect BadgeRect(const gfx::Rect& bounds,
                    const std::string& text,
                    int icon_width) {
  if (text.empty())
   return gfx::Rect(0, 0);

  SkPaint* text_paint = badge_util::GetBadgeTextPaintSingleton();
  text_paint->setTextSize(SkFloatToScalar(kTextSize));

  // Calculate text width. We clamp it to a max size.
  SkScalar sk_text_width = text_paint->measureText(text.c_str(), text.size());
  int text_width = std::min(kMaxTextWidth, SkScalarFloor(sk_text_width));

  // Calculate badge size. It is clamped to a min width just because it looks
  // silly if it is too skinny.
  int badge_width = text_width + kPadding * 2;
  // Force the pixel width of badge to be either odd (if the icon width is odd)
  // or even otherwise. If there is a mismatch you get http://crbug.com/26400.
  if (icon_width != 0 && (badge_width % 2 != icon_width % 2))
    badge_width += 1;
  badge_width = std::max(kBadgeHeight, badge_width);

  // Paint the badge background color in the right location. It is usually
  // right-aligned, but it can also be center-aligned if it is large.
  int rect_height = kBadgeHeight;
  int bottom_margin = kBottomMarginPageAction;
  int rect_y = bounds.bottom() - bottom_margin - kBadgeHeight;
  int rect_width = badge_width;
  int rect_x = (badge_width >= kCenterAlignThreshold) ?
      bounds.x() + (bounds.width() - badge_width) / 2 :
      bounds.right() - badge_width;

  return gfx::Rect(rect_x-1, rect_y-1, rect_width, rect_height);
}

void PaintBadge(gfx::Canvas* canvas,
                const gfx::Rect& bounds,
                const std::string& text,
                const SkColor& text_color_in,
                const SkColor& background_color_in,
                int icon_width,
                extensions::Extension::ActionInfo::Type action_type) {
  if (text.empty())
   return;

  SkColor text_color = SK_ColorWHITE;

  SkColor background_color_bottom = SkColorSetARGB(0xff, 0x9d, 0x00, 0x00);
  SkColor background_color_top    = SkColorSetARGB(0xff, 0xfb, 0x00, 0x00);

  canvas->Save();

  SkPaint* text_paint = badge_util::GetBadgeTextPaintSingleton();
  text_paint->setTextSize(SkFloatToScalar(kTextSize));
  text_paint->setColor(text_color);

  // Calculate text width. We clamp it to a max size.
  SkScalar sk_text_width = text_paint->measureText(text.c_str(), text.size());
  int text_width = std::min(kMaxTextWidth, SkScalarFloor(sk_text_width));

  // Calculate badge size. It is clamped to a min width just because it looks
  // silly if it is too skinny.
  int badge_width = text_width + kPadding * 2;
  // Force the pixel width of badge to be either odd (if the icon width is odd)
  // or even otherwise. If there is a mismatch you get http://crbug.com/26400.
  if (icon_width != 0 && (badge_width % 2 != icon_width % 2))
    badge_width += 1;
  badge_width = std::max(kBadgeHeight, badge_width);

  // Paint the badge background color in the right location. It is usually
  // right-aligned, but it can also be center-aligned if it is large.
  int rect_height = kBadgeHeight;
  int bottom_margin =
      action_type == extensions::Extension::ActionInfo::TYPE_BROWSER ?
      kBottomMarginBrowserAction : kBottomMarginPageAction;
  int rect_y = bounds.bottom() - bottom_margin - kBadgeHeight;
  int rect_width = badge_width;
  int rect_x = (badge_width >= kCenterAlignThreshold) ?
      bounds.x() + (bounds.width() - badge_width) / 2 :
      bounds.right() - badge_width;
  gfx::Rect rect(rect_x, rect_y, rect_width-2, rect_height-2);

  // Draw background
  SkPoint pts[2] = { { 0, rect_y + rect_height }, { 0, rect_y } };
  SkColor colors[2] = { background_color_bottom, background_color_top };
  skia::RefPtr<SkShader> gradient_shader = skia::AdoptRef(
      SkGradientShader::CreateLinear(pts, colors, NULL, 2,
                                     SkShader::kClamp_TileMode));
  SkPaint rect_paint;
  rect_paint.setStyle(SkPaint::kFill_Style);
  rect_paint.setAntiAlias(true);
  rect_paint.setShader(gradient_shader.get());
  canvas->DrawRoundRect(rect, 8, rect_paint);

  // Add highlight
  canvas->Save();
  // Add clip
  SkPath path;
  path.addRoundRect(gfx::RectToSkRect(rect),
                    SkIntToScalar(8), SkIntToScalar(8));
  canvas->ClipPath(path);
  rect.set_y(rect.y()-rect.height()/2);
  rect_paint.setShader(NULL);
  rect_paint.setColor(SkColorSetARGB(0x4c, 0xff, 0xff, 0xff));
  canvas->DrawRoundRect(rect, 8, rect_paint);
  rect.set_y(rect.y()+rect.height()/2);
  canvas->Restore();

  // Draw outline with shadow
  skia::RefPtr<SkBlurDrawLooper> blur_looper = skia::AdoptRef(
      new SkBlurDrawLooper(SkIntToScalar(1), SkIntToScalar(0), SkIntToScalar(1),
            SkColorSetARGB(0x66, 0x00, 0x00, 0x00), // 40% transparent black
            SkBlurDrawLooper::kIgnoreTransform_BlurFlag |
              SkBlurDrawLooper::kOverrideColor_BlurFlag |
              SkBlurDrawLooper::kHighQuality_BlurFlag));
  rect_paint.setShader(NULL);
  rect_paint.setLooper(blur_looper.get());
  rect_paint.setStyle(SkPaint::kStroke_Style);
  rect_paint.setStrokeWidth(2);
  rect_paint.setColor(SK_ColorWHITE);
  canvas->DrawRoundRect(rect, 8, rect_paint);

  // Finally, draw the text centered within the badge. We set a clip in case the
  // text was too large.
  gfx::Rect rect2(rect_x-1, rect_y+1, rect_width, rect_height);
  rect.Inset(kPadding, 0);
  canvas->ClipRect(rect);
  canvas->sk_canvas()->drawText(
      text.c_str(), text.size(),
      SkFloatToScalar(rect2.x() +
                      static_cast<float>(rect2.width() - text_width) / 2),
      SkFloatToScalar(rect2.y() + kTextSize + kTopTextPadding),
      *text_paint);
  canvas->Restore();
}

}  // namespace badge_util
