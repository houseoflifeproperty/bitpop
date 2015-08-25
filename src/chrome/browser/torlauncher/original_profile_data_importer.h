// BitPop browser. Tor launcher integration part.
// Copyright (C) 2015 BitPop AS
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

#ifndef CHROME_BROWSER_TORLAUNCHER_ORIGINAL_PROFILE_DATA_IMPORTER_H_
#define CHROME_BROWSER_TORLAUNCHER_ORIGINAL_PROFILE_DATA_IMPORTER_H_

#include "base/basictypes.h"
#include "base/compiler_specific.h"
#include "base/files/file_path.h"
#include "base/files/important_file_writer.h"
#include "base/memory/ref_counted.h"
#include "base/memory/scoped_ptr.h"
#include "base/memory/scoped_vector.h"
#include "base/memory/weak_ptr.h"
#include "components/bookmarks/browser/bookmark_node.h"
#include "components/bookmarks/browser/bookmark_storage.h"

class Profile;

namespace base {
class SequencedTaskRunner;
}

namespace bookmarks {
class BookmarkLoadDetails;
}

class OriginalProfileDataImporter
  : public base::RefCountedThreadSafe<OriginalProfileDataImporter> {
 public:
  OriginalProfileDataImporter(
      Profile *dst_profile,
      const base::FilePath& src_profile_path,
      const scoped_refptr<base::SequencedTaskRunner>& sequenced_task_runner);

  // These functions return true if the corresponding model has been loaded.
  // If the models haven't been loaded, the importer waits to run until they've
  // completed.
  bool BookmarkModelIsLoaded() const;
  // bool TemplateURLServiceIsLoaded() const;

  // Loads the bookmarks into the model, notifying the model when done. This
  // takes ownership of |details| and send the |OnLoadFinished| callback from
  // a task in |task_runner|. See BookmarkLoadDetails for details.
  void LoadBookmarks(
      const scoped_refptr<base::SequencedTaskRunner>& ui_task_runner);

  // Callback from backend after loading the bookmark file.
  void OnBookmarksLoadFinished(
      scoped_ptr<bookmarks::BookmarkLoadDetails> details);

 private:
  friend class base::RefCountedThreadSafe<OriginalProfileDataImporter>;

  virtual ~OriginalProfileDataImporter();

  void CopyBookmarkFolder(const bookmarks::BookmarkNode* src,
                          const bookmarks::BookmarkNode* dst);

  scoped_ptr<bookmarks::BookmarkLoadDetails> CreateLoadDetails();

  int64 generate_next_node_id();

  bookmarks::BookmarkPermanentNode* CreatePermanentNode(
      bookmarks::BookmarkNode::Type type);

  bookmarks::BookmarkPermanentNodeList LoadExtraNodes(int64* next_node_id);

  // Data members:

  Profile *dst_profile_;
  base::FilePath src_profile_path_;

  // Sequenced task runner where file I/O operations will be performed at.
  scoped_refptr<base::SequencedTaskRunner> sequenced_task_runner_;

  int64 next_node_id_;

  scoped_ptr<bookmarks::BookmarkLoadDetails> load_details_;

  base::WeakPtrFactory<OriginalProfileDataImporter> weak_factory_;

  DISALLOW_COPY_AND_ASSIGN(OriginalProfileDataImporter);
};

#endif  // CHROME_BROWSER_TORLAUNCHER_ORIGINAL_PROFILE_DATA_IMPORTER_H_
