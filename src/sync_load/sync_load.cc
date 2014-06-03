// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <cctype>
#include <inttypes.h>
#include <cstddef>
#include <cstdio>
#include <string>

#include <algorithm>
#include <fstream>
#include <functional>
#include <iostream>
#include <locale>
#include <string>
#include <vector>

#include "base/at_exit.h"
#include "base/base64.h"
#include "base/command_line.h"
#include "base/compiler_specific.h"
#include "base/debug/stack_trace.h"
#include "base/file_util.h"
#include "base/json/json_writer.h"
#include "base/logging.h"
#include "base/memory/ref_counted.h"
#include "base/memory/scoped_ptr.h"
#include "base/memory/weak_ptr.h"
#include "base/message_loop.h"
#include "base/rand_util.h"
#include "base/scoped_temp_dir.h"
#include "base/string_number_conversions.h"
#include "base/task_runner.h"
#include "base/time.h"
#include "base/timer.h"
#include "base/threading/thread.h"
#include "content/public/common/page_transition_types.h"
#include "jingle/notifier/base/notification_method.h"
#include "jingle/notifier/base/notifier_options.h"
#include "net/base/host_port_pair.h"
#include "net/base/host_resolver.h"
#include "net/base/network_change_notifier.h"
#include "net/base/transport_security_state.h"
#include "net/url_request/url_request_test_util.h"
#include "sync/engine/conflict_resolver.h"
#include "sync/engine/syncer_types.h"
#include "sync/engine/throttled_data_type_tracker.h"
#include "sync/internal_api/public/base/model_type.h"
#include "sync/internal_api/public/base_node.h"
#include "sync/internal_api/public/engine/passive_model_worker.h"
#include "sync/internal_api/public/http_bridge.h"
#include "sync/internal_api/public/internal_components_factory_impl.h"
#include "sync/internal_api/public/base/model_type.h"
#include "sync/internal_api/public/read_node.h"
#include "sync/internal_api/public/read_transaction.h"
#include "sync/internal_api/public/sync_manager.h"
#include "sync/internal_api/public/sync_manager_factory.h"
#include "sync/internal_api/public/util/report_unrecoverable_error_function.h"
#include "sync/internal_api/public/util/unrecoverable_error_handler.h"
#include "sync/internal_api/public/util/weak_handle.h"
#include "sync/internal_api/public/write_node.h"
#include "sync/internal_api/public/write_transaction.h"
#include "sync/js/js_event_details.h"
#include "sync/js/js_event_handler.h"
#include "sync/notifier/invalidation_state_tracker.h"
#include "sync/notifier/sync_notifier.h"
#include "sync/notifier/sync_notifier_factory.h"
#include "sync/syncable/syncable_id.h"
#include "sync/syncable/write_transaction.h"
#include "sync/test/fake_encryptor.h"
#include "sync/test/fake_extensions_activity_monitor.h"

#if defined(OS_MACOSX)
#include "base/mac/scoped_nsautorelease_pool.h"
#endif

// This is a simple utility that initializes a sync client and
// prints out any events.

// TODO(akalin): Refactor to combine shared code with
// sync_listen_notifications.
namespace syncer {
namespace {

const char kEmailSwitch[] = "email";
const char kTokenSwitch[] = "token";
const char kXmppHostPortSwitch[] = "xmpp-host-port";
const char kXmppTrySslTcpFirstSwitch[] = "xmpp-try-ssltcp-first";
const char kXmppAllowInsecureConnectionSwitch[] =
    "xmpp-allow-insecure-connection";
const char kNotificationMethodSwitch[] = "notification-method";
const char kHttpSyncServerAndPath[] = "http-sync-server-and-path";
const char kHttpSyncPort[] = "http-sync-server-port";
const char kHttpSyncUseSsl[] = "http-sync-server-use-ssl";
const char kCreateRandomBookmark[] = "create-random-bookmark-every";
const char kCreateRandomHistoryRecord[] = "create-random-history-record-every";
const char kFetchDBFromServerOnLaunch[] = "fetch-db-from-server-on-launch";
const char kUserDir[] = "user-dir";

const int kLoopDelayMs = 50;

void DoNothing() {
  std::printf("Retry...");
}

// trim from start
static inline std::string &ltrim(std::string &s) {
        s.erase(s.begin(), std::find_if(s.begin(), s.end(), std::not1(std::ptr_fun<int, int>(std::isspace))));
        return s;
}

// trim from end
static inline std::string &rtrim(std::string &s) {
        s.erase(std::find_if(s.rbegin(), s.rend(), std::not1(std::ptr_fun<int, int>(std::isspace))).base(), s.end());
        return s;
}

// trim from both ends
static inline std::string &trim(std::string &s) {
        return ltrim(rtrim(s));
}

static std::string generateRandomClientTag() {
  static const char mix[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890!@#$%^&*()_+-=[]{}\"'\\|/?:;<>,.";
  static const size_t len = sizeof(mix) / sizeof(char);

  std::string s;
  static const size_t tag_len = 16;
  for (int i = 0; i < (int)tag_len; i++) {
    s.push_back(mix[base::RandInt(0, len-1)]);
  }
  s += base::Int64ToString(base::Time::Now().ToInternalValue());

  return s;
}

class EntityCreationTasks {
  public:
    explicit EntityCreationTasks(SyncManager* sync_manager);
    ~EntityCreationTasks();

    void StartBookmarkTimer(int seconds);
    void StartHistoryTimer(int seconds);

    void StopBookmarkTimer();
    void StopHistoryTimer();

    void DoBookmarkStuff();
    void DoHistoryStuff();

    bool can_do() const { return can_do_; }
  private:
    int64 MakeNode(ModelType model_type,
                   const std::string& client_tag);
    int64 MakeNodeWithParent(ModelType model_type,
                             const std::string& client_tag,
                             int64 parent_id);
    int64 MakeFolderWithParent(ModelType model_type,
                               int64 parent_id,
                               BaseNode* predecessor);

    base::RepeatingTimer<EntityCreationTasks> bookmark_timer_;
    base::RepeatingTimer<EntityCreationTasks> history_timer_;
    SyncManager* sync_manager_;
    std::vector<std::string> words_;
    std::vector<std::string> urls_;
    bool can_do_;

};

EntityCreationTasks::EntityCreationTasks(SyncManager* sync_manager) :
  sync_manager_(sync_manager), can_do_(true) {
    std::ifstream dict_stream("dict.txt", std::ios_base::in);
    std::ifstream url_stream("data.txt", std::ios_base::in);

    words_.clear();
    urls_.clear();

    std::string line;
    while (std::getline(dict_stream, line, '\n'))
      words_.push_back(trim(line));
    while (std::getline(url_stream, line, '\n'))
      urls_.push_back(trim(line));

    if (words_.empty() || urls_.empty()) {
      can_do_ = false;
      std::fprintf(stderr, "No files dict.txt and data.txt in current dir.\n");
    }
}

EntityCreationTasks::~EntityCreationTasks() {
  bookmark_timer_.Stop();
  history_timer_.Stop();
}

void EntityCreationTasks::StartBookmarkTimer(int seconds) {
  if (seconds > 0) {
    bookmark_timer_.Start(FROM_HERE, TimeDelta::FromSeconds(seconds),
        this, &EntityCreationTasks::DoBookmarkStuff);
  }
  else
    std::fprintf(stderr, "Bad parameter for bookmarks creation interval.\n");
}

void EntityCreationTasks::StartHistoryTimer(int seconds) {
  if (seconds > 0) {
    history_timer_.Start(FROM_HERE, TimeDelta::FromSeconds(seconds),
        this, &EntityCreationTasks::DoHistoryStuff);
  }
  else
    std::fprintf(stderr, "Bad parameter for history creation interval.\n");
}


void EntityCreationTasks::DoBookmarkStuff() {
  std::string title = words_[base::RandInt(0, words_.size()-1)] + " " +
                      words_[base::RandInt(0, words_.size()-1)];
  GURL url(urls_[base::RandInt(0, urls_.size()-1)]);

  {
    WriteTransaction trans(FROM_HERE, sync_manager_->GetUserShare());
    ReadNode bar_node(&trans);
    bar_node.InitByTagLookup("bookmark_bar");

    WriteNode node(&trans);
    if (!node.InitByCreation(BOOKMARKS, bar_node, NULL)) {
      std::fprintf(stderr, "Bookmark node.InitByCreation() call failed.\n");
      return;
    }

    node.SetIsFolder(false);
    node.SetTitle(UTF8ToWide(title));
    node.SetURL(url);
  }

  std::printf("+ Bookmark creation (\"%s\", %s) possibly succeeded...\n",
              title.c_str(), url.spec().c_str());
}

void EntityCreationTasks::DoHistoryStuff() {
  std::string title =
    words_[base::RandInt(0, words_.size()-1)] + " " +
    words_[base::RandInt(0, words_.size()-1)] + " " +
    words_[base::RandInt(0, words_.size()-1)];
  GURL url(urls_[base::RandInt(0, urls_.size()-1)]);

  {
    WriteTransaction trans(FROM_HERE, sync_manager_->GetUserShare());
    ReadNode bar_node(&trans);
    bar_node.InitByTagLookup("google_chrome_typed_urls");

    WriteNode node(&trans);
    if (!node.InitUniqueByCreation(TYPED_URLS, bar_node, generateRandomClientTag())) {
      std::fprintf(stderr, "Typed url node.InitByCreation() call failed.\n");
      return;
    }

    sync_pb::TypedUrlSpecifics specifics;
    int n = base::RandInt(1, 50);
    for (int i = 0; i < n; i++) {
      base::Time t(base::Time::Now());
      specifics.add_visits(t.ToInternalValue());
      specifics.add_visit_transitions(content::PAGE_TRANSITION_TYPED |
                                      content::PAGE_TRANSITION_FROM_ADDRESS_BAR |
                                      content::PAGE_TRANSITION_CHAIN_START);
    }

    specifics.set_title(title.c_str());
    specifics.set_url(url.spec().c_str());
    specifics.set_hidden(false);
    node.SetTypedUrlSpecifics(specifics);

    node.SetIsFolder(false);
    node.SetTitle(UTF8ToWide(url.spec()));
  }

  std::printf("+ Typed URL creation (\"%s\", %s) possibly succeeded...\n",
              title.c_str(), url.spec().c_str());
}

// Makes a non-folder child of the root node.  Returns the id of the
// newly-created node.
int64 EntityCreationTasks::MakeNode(ModelType model_type,
               const std::string& client_tag) {
  UserShare* share = sync_manager_->GetUserShare();
  WriteTransaction trans(FROM_HERE, share);
  ReadNode root_node(&trans);
  root_node.InitByRootLookup();
  WriteNode node(&trans);
  //WriteNode::InitUniqueByCreationResult result =
  node.InitUniqueByCreation(model_type, root_node, client_tag);
  //EXPECT_EQ(WriteNode::INIT_SUCCESS, result);
  node.SetIsFolder(false);
  return node.GetId();
}

// Makes a non-folder child of a non-root node. Returns the id of the
// newly-created node.
int64 EntityCreationTasks::MakeNodeWithParent(ModelType model_type,
                         const std::string& client_tag,
                         int64 parent_id) {
  UserShare* share = sync_manager_->GetUserShare();
  WriteTransaction trans(FROM_HERE, share);
  ReadNode parent_node(&trans);
  //EXPECT_EQ(BaseNode::INIT_OK, parent_node.InitByIdLookup(parent_id));
  parent_node.InitByIdLookup(parent_id);
  WriteNode node(&trans);
  //WriteNode::InitUniqueByCreationResult result =
  node.InitUniqueByCreation(model_type, parent_node, client_tag);
  //EXPECT_EQ(WriteNode::INIT_SUCCESS, result);
  node.SetIsFolder(false);
  return node.GetId();
}

// Makes a folder child of a non-root node. Returns the id of the
// newly-created node.
int64 EntityCreationTasks::MakeFolderWithParent(ModelType model_type,
                           int64 parent_id,
                           BaseNode* predecessor) {
  UserShare* share = sync_manager_->GetUserShare();
  WriteTransaction trans(FROM_HERE, share);
  ReadNode parent_node(&trans);
  //EXPECT_EQ(BaseNode::INIT_OK, parent_node.InitByIdLookup(parent_id));
  parent_node.InitByIdLookup(parent_id);
  WriteNode node(&trans);
  //EXPECT_TRUE(node.InitByCreation(model_type, parent_node, predecessor));
  node.InitByCreation(model_type, parent_node, predecessor);
  node.SetIsFolder(true);
  return node.GetId();
}

void StartSyncingNormally(SyncManager* sync_manager,
                          const ModelSafeRoutingInfo& routing_info,
                          MessageLoop& sync_loop,
                          EntityCreationTasks* tasks,
                          int createRandomBookmarkInterval,
                          int createRandomHistoryRecordInterval
                          ) {
  sync_manager->StartSyncingNormally(routing_info);

  if (createRandomBookmarkInterval >= 0) {
    if (createRandomBookmarkInterval == 0) {
      sync_loop.PostTask(FROM_HERE,
                         base::Bind(&EntityCreationTasks::DoBookmarkStuff,
                                    base::Unretained(tasks)));
    }
    else
      sync_loop.PostTask(FROM_HERE,
                         base::Bind(&EntityCreationTasks::StartBookmarkTimer,
                                    base::Unretained(tasks),
                                    createRandomBookmarkInterval));
  }

  if (createRandomHistoryRecordInterval >= 0) {
    if (createRandomHistoryRecordInterval == 0) {
      sync_loop.PostTask(FROM_HERE,
                         base::Bind(&EntityCreationTasks::DoHistoryStuff,
                                    base::Unretained(tasks)));
    }
    else
      sync_loop.PostTask(FROM_HERE,
                         base::Bind(&EntityCreationTasks::StartHistoryTimer,
                                    base::Unretained(tasks),
                                    createRandomHistoryRecordInterval));
  }
}

class NullInvalidationStateTracker
    : public base::SupportsWeakPtr<NullInvalidationStateTracker>,
      public InvalidationStateTracker {
 public:
  NullInvalidationStateTracker() {}
  virtual ~NullInvalidationStateTracker() {}

  virtual InvalidationVersionMap GetAllMaxVersions() const OVERRIDE {
    return InvalidationVersionMap();
  }

  virtual void SetMaxVersion(
      const invalidation::ObjectId& id,
      int64 max_invalidation_version) OVERRIDE {
    VLOG(1) << "Setting max invalidation version for "
            << ObjectIdToString(id) << " to " << max_invalidation_version;
  }

  virtual std::string GetInvalidationState() const OVERRIDE {
    return std::string();
  }

  virtual void SetInvalidationState(const std::string& state) OVERRIDE {
    std::string base64_state;
    CHECK(base::Base64Encode(state, &base64_state));
    VLOG(1) << "Setting invalidation state to: " << base64_state;
  }
};

// Needed to use a real host resolver.
class MyTestURLRequestContext : public TestURLRequestContext {
 public:
  MyTestURLRequestContext() : TestURLRequestContext(true) {
    context_storage_.set_host_resolver(
        net::CreateSystemHostResolver(
            net::HostResolver::kDefaultParallelism,
            net::HostResolver::kDefaultRetryAttempts,
            NULL));
    context_storage_.set_transport_security_state(
        new net::TransportSecurityState());
    Init();
  }

  virtual ~MyTestURLRequestContext() {}
};

class MyTestURLRequestContextGetter : public TestURLRequestContextGetter {
 public:
  explicit MyTestURLRequestContextGetter(
      const scoped_refptr<base::MessageLoopProxy>& io_message_loop_proxy)
      : TestURLRequestContextGetter(io_message_loop_proxy) {}

  virtual TestURLRequestContext* GetURLRequestContext() OVERRIDE {
    // Construct |context_| lazily so it gets constructed on the right
    // thread (the IO thread).
    if (!context_.get())
      context_.reset(new MyTestURLRequestContext());
    return context_.get();
  }

 private:
  virtual ~MyTestURLRequestContextGetter() {}

  scoped_ptr<MyTestURLRequestContext> context_;
};

// TODO(akalin): Use system encryptor once it's moved to sync/.
class NullEncryptor : public Encryptor {
 public:
  virtual ~NullEncryptor() {}

  virtual bool EncryptString(const std::string& plaintext,
                             std::string* ciphertext) OVERRIDE {
    *ciphertext = plaintext;
    return true;
  }

  virtual bool DecryptString(const std::string& ciphertext,
                             std::string* plaintext) OVERRIDE {
    *plaintext = ciphertext;
    return true;
  }
};

std::string ValueToString(const Value& value) {
  std::string str;
  base::JSONWriter::Write(&value, &str);
  return str;
}

class LoggingChangeDelegate : public SyncManager::ChangeDelegate {
 public:
  virtual ~LoggingChangeDelegate() {}

  virtual void OnChangesApplied(
      ModelType model_type,
      const BaseTransaction* trans,
      const ImmutableChangeRecordList& changes) OVERRIDE {
    LOG(INFO) << "Changes applied for "
              << ModelTypeToString(model_type);
    size_t i = 1;
    size_t change_count = changes.Get().size();
    for (ChangeRecordList::const_iterator it =
             changes.Get().begin(); it != changes.Get().end(); ++it) {
      scoped_ptr<base::DictionaryValue> change_value(it->ToValue());
      LOG(INFO) << "Change (" << i << "/" << change_count << "): "
                << ValueToString(*change_value);
      if (it->action != ChangeRecord::ACTION_DELETE) {
        ReadNode node(trans);
        CHECK_EQ(node.InitByIdLookup(it->id), BaseNode::INIT_OK);
        scoped_ptr<base::DictionaryValue> details(node.GetDetailsAsValue());
        VLOG(1) << "Details: " << ValueToString(*details);
      }
      ++i;
    }
  }

  virtual void OnChangesComplete(ModelType model_type) OVERRIDE {
    LOG(INFO) << "Changes complete for "
              << ModelTypeToString(model_type);
  }
};

class LoggingUnrecoverableErrorHandler
    : public UnrecoverableErrorHandler {
 public:
  virtual ~LoggingUnrecoverableErrorHandler() {}

  virtual void OnUnrecoverableError(const tracked_objects::Location& from_here,
                                    const std::string& message) OVERRIDE {
    if (LOG_IS_ON(ERROR)) {
      logging::LogMessage(from_here.file_name(), from_here.line_number(),
                          logging::LOG_ERROR).stream()
          << message;
    }
  }
};

class LoggingJsEventHandler
    : public JsEventHandler,
      public base::SupportsWeakPtr<LoggingJsEventHandler> {
 public:
  virtual ~LoggingJsEventHandler() {}

  virtual void HandleJsEvent(
      const std::string& name,
      const JsEventDetails& details) OVERRIDE {
    VLOG(1) << name << ": " << details.ToString();
  }
};

void LogUnrecoverableErrorContext() {
  base::debug::StackTrace stack_trace;
  stack_trace.PrintBacktrace();
}

notifier::NotifierOptions ParseNotifierOptions(
    const CommandLine& command_line,
    const scoped_refptr<net::URLRequestContextGetter>&
        request_context_getter) {
  notifier::NotifierOptions notifier_options;
  notifier_options.request_context_getter = request_context_getter;

  if (command_line.HasSwitch(kXmppHostPortSwitch)) {
    notifier_options.xmpp_host_port =
        net::HostPortPair::FromString(
            command_line.GetSwitchValueASCII(kXmppHostPortSwitch));
    LOG(INFO) << "Using " << notifier_options.xmpp_host_port.ToString()
              << " for test sync notification server.";
  }

  notifier_options.try_ssltcp_first =
      command_line.HasSwitch(kXmppTrySslTcpFirstSwitch);
  LOG_IF(INFO, notifier_options.try_ssltcp_first)
      << "Trying SSL/TCP port before XMPP port for notifications.";

  notifier_options.allow_insecure_connection =
      command_line.HasSwitch(kXmppAllowInsecureConnectionSwitch);
  LOG_IF(INFO, notifier_options.allow_insecure_connection)
      << "Allowing insecure XMPP connections.";

  if (command_line.HasSwitch(kNotificationMethodSwitch)) {
    notifier_options.notification_method =
        notifier::StringToNotificationMethod(
            command_line.GetSwitchValueASCII(kNotificationMethodSwitch));
  }

  return notifier_options;
}


int SyncClientMain(int argc, char* argv[]) {
#if defined(OS_MACOSX)
  base::mac::ScopedNSAutoreleasePool pool;
#endif
  base::AtExitManager exit_manager;
  CommandLine::Init(argc, argv);
  logging::InitLogging(
      NULL,
      logging::LOG_ONLY_TO_SYSTEM_DEBUG_LOG,
      logging::LOCK_LOG_FILE,
      logging::DELETE_OLD_LOG_FILE,
      logging::DISABLE_DCHECK_FOR_NON_OFFICIAL_RELEASE_BUILDS);

  MessageLoop sync_loop;
  base::Thread io_thread("IO thread");
  base::Thread::Options options;
  options.message_loop_type = MessageLoop::TYPE_IO;
  io_thread.StartWithOptions(options);

  // Parse command line.
  const CommandLine& command_line = *CommandLine::ForCurrentProcess();
  SyncCredentials credentials;
  credentials.email = command_line.GetSwitchValueASCII(kEmailSwitch);
  credentials.sync_token = command_line.GetSwitchValueASCII(kTokenSwitch);

  std::string sync_server_and_path =
      command_line.GetSwitchValueASCII(kHttpSyncServerAndPath);
  int sync_server_port = 0;
  bool conversion_ok = base::StringToInt(
      command_line.GetSwitchValueASCII(kHttpSyncPort),
      &sync_server_port);
  bool use_ssl = command_line.HasSwitch(kHttpSyncUseSsl);

  // TODO(akalin): Write a wrapper script that gets a token for an
  // email and password and passes that in to this utility.
  if (credentials.email.empty() || credentials.sync_token.empty() ||
        sync_server_and_path.empty() || !conversion_ok) {
    std::printf("Usage: %s --%s=foo@bar.com --%s=token\n"
                "--%s=host/path --%s=port\n"
                "[--%s]\n"
                "[--%s=host:port]\n"
                "[--%s] [--%s]\n"
                "[--%s=(server|p2p)]\n"
                "[--%s=(seconds|0 <for creating only once>)]\n"
                "[--%s=(seconds|0 <for creating only once>)]\n"
                "[--%s]\n"
                "[--%s=/path/to/user/database/directory]\n"
                "   ^- Create temporary autocleaning directory if not defined.\n",
                argv[0],
                kEmailSwitch, kTokenSwitch, kHttpSyncServerAndPath,
                kHttpSyncPort, kHttpSyncUseSsl, kXmppHostPortSwitch,
                kXmppTrySslTcpFirstSwitch,
                kXmppAllowInsecureConnectionSwitch,
                kNotificationMethodSwitch,
                kCreateRandomBookmark, kCreateRandomHistoryRecord,
                kFetchDBFromServerOnLaunch, kUserDir);
    return -1;
  }

  // Set up objects that monitor the network.
  scoped_ptr<net::NetworkChangeNotifier> network_change_notifier(
      net::NetworkChangeNotifier::Create());

  // Set up sync notifier factory.
  const scoped_refptr<MyTestURLRequestContextGetter> context_getter =
      new MyTestURLRequestContextGetter(io_thread.message_loop_proxy());
  const notifier::NotifierOptions& notifier_options =
      ParseNotifierOptions(command_line, context_getter);
  const char kClientInfo[] = "sync_listen_notifications";
  NullInvalidationStateTracker null_invalidation_state_tracker;
  SyncNotifierFactory sync_notifier_factory(
      notifier_options, kClientInfo,
      null_invalidation_state_tracker.AsWeakPtr());

  // Set up database directory for the syncer.
  FilePath directory_for_syncer;
  if (command_line.HasSwitch(kUserDir)) {
    FilePath user_dir(command_line.GetSwitchValueASCII(kUserDir));
    if (file_util::CreateDirectory(user_dir))
      directory_for_syncer = user_dir;
  }

  ScopedTempDir database_dir;
  if (directory_for_syncer.empty()) {
    CHECK(database_dir.CreateUniqueTempDir());
    directory_for_syncer = database_dir.path();
  }

  // Set up model type parameters.
  const ModelTypeSet model_types = ModelTypeSet::All();
  ModelSafeRoutingInfo routing_info;
  for (ModelTypeSet::Iterator it = model_types.First();
       it.Good(); it.Inc()) {
    routing_info[it.Get()] = GROUP_PASSIVE;
  }
  scoped_refptr<PassiveModelWorker> passive_model_safe_worker =
      new PassiveModelWorker(&sync_loop);
  std::vector<ModelSafeWorker*> workers;
  workers.push_back(passive_model_safe_worker.get());

  // Set up sync manager.
  SyncManagerFactory sync_manager_factory;
  scoped_ptr<SyncManager> sync_manager =
      sync_manager_factory.CreateSyncManager("sync_client manager");
  LoggingJsEventHandler js_event_handler;

  // Used only by RefreshNigori(), so it's okay to leave this as NULL.
  const scoped_refptr<base::TaskRunner> blocking_task_runner = NULL;
  const char kUserAgent[] = "sync_client";
  // TODO(akalin): Replace this with just the context getter once
  // HttpPostProviderFactory is removed.
  scoped_ptr<HttpPostProviderFactory> post_factory(
      new HttpBridgeFactory(context_getter, kUserAgent));
  // Used only when committing bookmarks, so it's okay to leave this
  // as NULL.
  FakeExtensionsActivityMonitor extensions_activity_monitor;
  LoggingChangeDelegate change_delegate;
  const char kRestoredKeyForBootstrapping[] = "";
  const char kRestoredKeystoreKeyForBootstrapping[] = "";
  NullEncryptor null_encryptor;
  LoggingUnrecoverableErrorHandler unrecoverable_error_handler;
  sync_manager->Init(directory_for_syncer,
                    WeakHandle<JsEventHandler>(
                        js_event_handler.AsWeakPtr()),
                    sync_server_and_path,
                    sync_server_port,
                    use_ssl,
                    blocking_task_runner,
                    post_factory.Pass(),
                    workers,
                    &extensions_activity_monitor,
                    &change_delegate,
                    credentials,
                    scoped_ptr<SyncNotifier>(
                        sync_notifier_factory.CreateSyncNotifier()),
                    kRestoredKeyForBootstrapping,
                    kRestoredKeystoreKeyForBootstrapping,
                    true,  // enable keystore encryption
                    scoped_ptr<InternalComponentsFactory>(
                        new InternalComponentsFactoryImpl()),
                    &null_encryptor,
                    &unrecoverable_error_handler,
                    &LogUnrecoverableErrorContext);
  // TODO(akalin): Avoid passing in model parameters multiple times by
  // organizing handling of model types.
  sync_manager->UpdateEnabledTypes(model_types);

  if (command_line.HasSwitch(kFetchDBFromServerOnLaunch)) {
    sync_manager->ConfigureSyncer(
        CONFIGURE_REASON_NEW_CLIENT,
        model_types,
        routing_info,
        base::Bind(&SyncManager::StartSyncingNormally,
            base::Unretained(sync_manager.get()),
            base::ConstRef(routing_info)),
        base::Bind(&DoNothing));
  }

  int bookmark_create_seconds = -1;
  bool b_conversion_ok = command_line.HasSwitch(kCreateRandomBookmark) &&
        base::StringToInt(command_line.GetSwitchValueASCII(
            kCreateRandomBookmark), &bookmark_create_seconds);
  if (!b_conversion_ok)
    bookmark_create_seconds = -1; // Just in case StringToInt
                                  // will modify the initials

  int history_create_seconds = -1;
  bool h_conversion_ok = command_line.HasSwitch(kCreateRandomHistoryRecord) &&
        base::StringToInt(command_line.GetSwitchValueASCII(
            kCreateRandomHistoryRecord), &history_create_seconds);
  if (!h_conversion_ok)
    history_create_seconds = -1;  // Just in case StringToInt will modify
                                  // initials

  scoped_ptr<EntityCreationTasks> tasks(
      new EntityCreationTasks(sync_manager.get()));

  if (!tasks->can_do())
    return -1;

  StartSyncingNormally(sync_manager.get(), routing_info, sync_loop,
                       tasks.get(), bookmark_create_seconds,
                       history_create_seconds);

  sync_loop.Run();

  io_thread.Stop();
  return 0;
}

}  // namespace
}  // namespace syncer

int main(int argc, char* argv[]) {
  return syncer::SyncClientMain(argc, argv);
}
