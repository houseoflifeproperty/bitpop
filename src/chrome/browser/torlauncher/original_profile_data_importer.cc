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

#include "chrome/browser/torlauncher/original_profile_data_importer.h"

#include <set>

#include "base/files/file_path.h"
#include "base/files/file_util.h"
#include "base/json/json_file_value_serializer.h"
#include "base/prefs/pref_service.h"
#include "base/sequenced_task_runner.h"
#include "base/strings/string_number_conversions.h"
#include "base/strings/utf_string_conversions.h"
#include "chrome/browser/bookmarks/bookmark_model_factory.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/common/pref_names.h"
#include "components/bookmarks/browser/bookmark_codec.h"
#include "components/bookmarks/browser/bookmark_index.h"
#include "components/bookmarks/browser/bookmark_model.h"
#include "components/bookmarks/browser/bookmark_storage.h"
#include "components/bookmarks/common/bookmark_constants.h"
#include "grit/components_strings.h"
#include "ui/base/l10n/l10n_util.h"

using bookmarks::BookmarkCodec;
using bookmarks::BookmarkLoadDetails;
using bookmarks::BookmarkNode;
using bookmarks::BookmarkPermanentNode;
using bookmarks::BookmarkPermanentNodeList;
using bookmarks::BookmarkModel;

namespace {

void LoadCallback(const base::FilePath& path,
                  const base::WeakPtr<OriginalProfileDataImporter>& importer,
                  scoped_ptr<BookmarkLoadDetails> details,
                  base::SequencedTaskRunner* task_runner) {
  bool bookmark_file_exists = base::PathExists(path);
  if (bookmark_file_exists) {
    JSONFileValueDeserializer deserializer(path);
    scoped_ptr<base::Value> root(deserializer.Deserialize(NULL, NULL));

    if (root.get()) {
      // Building the index can take a while, so we do it on the background
      // thread.
      int64 max_node_id = 0;
      BookmarkCodec codec;
      codec.Decode(details->bb_node(), details->other_folder_node(),
                   details->mobile_folder_node(), &max_node_id, *root.get());
      details->set_max_id(std::max(max_node_id, details->max_id()));
      details->set_computed_checksum(codec.computed_checksum());
      details->set_stored_checksum(codec.stored_checksum());
      details->set_ids_reassigned(codec.ids_reassigned());
      details->set_model_meta_info_map(codec.model_meta_info_map());
      details->set_model_sync_transaction_version(
          codec.model_sync_transaction_version());
    }
  }

  // Load any extra root nodes now, after the IDs have been potentially
  // reassigned.
  details->LoadExtraNodes();

  task_runner->PostTask(
      FROM_HERE,
      base::Bind(&OriginalProfileDataImporter::OnBookmarksLoadFinished, importer,
                 base::Passed(&details)));
}

// // Generates a unique folder name. If |folder_name| is not unique, then this
// // repeatedly tests for '|folder_name| + (i)' until a unique name is found.
// base::string16 GenerateUniqueFolderName(BookmarkModel* model,
//                                         const base::string16& folder_name) {
//   // Build a set containing the bookmark bar folder names.
//   std::set<base::string16> existing_folder_names;
//   const BookmarkNode* bookmark_bar = model->bookmark_bar_node();
//   for (int i = 0; i < bookmark_bar->child_count(); ++i) {
//     const BookmarkNode* node = bookmark_bar->GetChild(i);
//     if (node->is_folder())
//       existing_folder_names.insert(node->GetTitle());
//   }

//   // If the given name is unique, use it.
//   if (existing_folder_names.find(folder_name) == existing_folder_names.end())
//     return folder_name;

//   // Otherwise iterate until we find a unique name.
//   for (size_t i = 1; i <= existing_folder_names.size(); ++i) {
//     base::string16 name = folder_name + base::ASCIIToUTF16(" (") +
//         base::IntToString16(i) + base::ASCIIToUTF16(")");
//     if (existing_folder_names.find(name) == existing_folder_names.end())
//       return name;
//   }

//   NOTREACHED();
//   return folder_name;
// }

// Shows the bookmarks toolbar.
void ShowBookmarkBar(Profile* profile) {
  profile->GetPrefs()->SetBoolean(bookmarks::prefs::kShowBookmarkBar, true);
}

}  // namespace

OriginalProfileDataImporter::OriginalProfileDataImporter(
    Profile *dst_profile,
    const base::FilePath& src_profile_path,
    const scoped_refptr<base::SequencedTaskRunner>& sequenced_task_runner)
      : dst_profile_(dst_profile),
        src_profile_path_(src_profile_path),
        next_node_id_(1),
        weak_factory_(this) {
  sequenced_task_runner_ = sequenced_task_runner.get();
}

OriginalProfileDataImporter::~OriginalProfileDataImporter() {

}

bool OriginalProfileDataImporter::BookmarkModelIsLoaded() const {
  return BookmarkModelFactory::GetForProfile(dst_profile_)->loaded();
}

void OriginalProfileDataImporter::LoadBookmarks(
    const scoped_refptr<base::SequencedTaskRunner>& ui_task_runner) {
  AddRef();
  base::FilePath bookmarksPath = src_profile_path_.Append(
      bookmarks::kBookmarksFileName);
  load_details_ = CreateLoadDetails();
  sequenced_task_runner_->PostTask(FROM_HERE,
                                   base::Bind(&LoadCallback,
                                              bookmarksPath,
                                              weak_factory_.GetWeakPtr(),
                                              base::Passed(&load_details_),
                                              ui_task_runner));
}

void OriginalProfileDataImporter::CopyBookmarkFolder(const BookmarkNode* src,
                                                     const BookmarkNode* dst) {
  DCHECK(dst->is_folder());
  if (src->empty())
    return;

  BookmarkModel* model = BookmarkModelFactory::GetForProfile(dst_profile_);
  DCHECK(model->loaded());

  typedef std::pair<const BookmarkNode*, const BookmarkNode*> FolderPair;
  std::set<FolderPair> folders_added_to;
  for (int index = 0; index < src->child_count(); ++index) {
    const BookmarkNode* src_child = src->GetChild(index);
    const BookmarkNode* dst_child = nullptr;
    for (int dindex = 0; dindex < dst->child_count(); ++dindex) {
      const BookmarkNode* dnode = dst->GetChild(dindex);
      if (src_child->type() == dnode->type() &&
         (
          (src_child->is_url() && src_child->url() == dnode->url()) ||
          (src_child->is_folder() && src_child->GetTitle() == dnode->GetTitle())
         )) {
        dst_child = dnode;
        break;
      }
    }
    if (dst_child && dst_child->is_folder()) {
      folders_added_to.insert(FolderPair(src_child, dst_child));
    }
    if (dst_child) {
      continue;
    }

    // if (dst_child == nullptr)
    if (src_child->is_folder()) {
      const BookmarkNode* folder_node =
          model->AddFolder(dst, dst->child_count(), src_child->GetTitle());
      folders_added_to.insert(FolderPair(src_child, folder_node));
    } else {  // is bookmark url
      model->AddURLWithCreationTimeAndMetaInfo(dst,
                                             dst->child_count(),
                                             src_child->GetTitle(),
                                             src_child->url(),
                                             src_child->date_added(),
                                             NULL);
    }
  }

  // In order to keep the imported-to folders from appearing in the 'recently
  // added to' combobox, reset their modified times.
  for (std::set<FolderPair>::const_iterator i =
           folders_added_to.begin();
       i != folders_added_to.end(); ++i) {
    CopyBookmarkFolder(i->first, i->second);
    model->ResetDateFolderModified(i->second);
  }
}

void OriginalProfileDataImporter::OnBookmarksLoadFinished(
    scoped_ptr<BookmarkLoadDetails> details) {
  BookmarkPermanentNode *bb_bookmarks = details->bb_node();
  BookmarkPermanentNode *mobile_folder_bookmarks =
      details->mobile_folder_node();
  BookmarkPermanentNode *other_folder_bookmarks = details->other_folder_node();
  //const BookmarkPermanentNodeList &extras_list = details->extra_nodes();

  if (!dst_profile_ ||
      (bb_bookmarks->empty() && mobile_folder_bookmarks->empty() &&
       other_folder_bookmarks->empty()))
    return;

  BookmarkModel* model = BookmarkModelFactory::GetForProfile(dst_profile_);
  DCHECK(model->loaded());

  model->BeginExtensiveChanges();

  CopyBookmarkFolder(bb_bookmarks, model->bookmark_bar_node());
  CopyBookmarkFolder(mobile_folder_bookmarks, model->mobile_node());
  CopyBookmarkFolder(other_folder_bookmarks, model->other_node());

  model->EndExtensiveChanges();

  ShowBookmarkBar(dst_profile_);

  Release();
}

scoped_ptr<BookmarkLoadDetails>
OriginalProfileDataImporter::CreateLoadDetails() {
  BookmarkPermanentNode* bb_node =
      CreatePermanentNode(BookmarkNode::BOOKMARK_BAR);
  BookmarkPermanentNode* other_node =
      CreatePermanentNode(BookmarkNode::OTHER_NODE);
  BookmarkPermanentNode* mobile_node =
      CreatePermanentNode(BookmarkNode::MOBILE);
  return scoped_ptr<BookmarkLoadDetails>(new BookmarkLoadDetails(
      bb_node,
      other_node,
      mobile_node,
      base::Bind(&OriginalProfileDataImporter::LoadExtraNodes,
                 base::Unretained(this)),
      NULL,
      next_node_id_));
}

int64 OriginalProfileDataImporter::generate_next_node_id() {
  return next_node_id_++;
}

BookmarkPermanentNode* OriginalProfileDataImporter::CreatePermanentNode(
    BookmarkNode::Type type) {
  DCHECK(type == BookmarkNode::BOOKMARK_BAR ||
         type == BookmarkNode::OTHER_NODE ||
         type == BookmarkNode::MOBILE);
  BookmarkPermanentNode* node =
      new BookmarkPermanentNode(generate_next_node_id());
  node->set_type(type);
  node->set_visible(true);

  int title_id;
  switch (type) {
    case BookmarkNode::BOOKMARK_BAR:
      title_id = IDS_BOOKMARK_BAR_FOLDER_NAME;
      break;
    case BookmarkNode::OTHER_NODE:
      title_id = IDS_BOOKMARK_BAR_OTHER_FOLDER_NAME;
      break;
    case BookmarkNode::MOBILE:
      title_id = IDS_BOOKMARK_BAR_MOBILE_FOLDER_NAME;
      break;
    default:
      NOTREACHED();
      title_id = IDS_BOOKMARK_BAR_FOLDER_NAME;
      break;
  }
  node->SetTitle(l10n_util::GetStringUTF16(title_id));
  return node;
}

BookmarkPermanentNodeList OriginalProfileDataImporter::LoadExtraNodes(
    int64* next_node_id) {
  BookmarkPermanentNodeList extra_nodes;
  return extra_nodes.Pass();
}
