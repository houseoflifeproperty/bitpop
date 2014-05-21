/*
 * Copyright 2011 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.ipc.invalidation.examples.android2;

import com.google.android.gcm.GCMRegistrar;
import com.google.ipc.invalidation.external.client.contrib.AndroidListener;
import com.google.ipc.invalidation.external.client.types.ObjectId;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;

import java.util.HashMap;
import java.util.Map;
import java.util.Map.Entry;

/**
 * A simple  sample application that displays information about object registrations and
 * versions.
 *
 * <p>To submit invalidations, you can use the ExampleServlet, e.g.:
 *
 * <p><code>
 * blaze run -- //java/com/google/ipc/invalidation/examples:ExampleServlet --publisherSpec="" \
       --port=8888 --channelUri="talkgadget.google.com" --use_lcs=false
 * </code>
 *
 * <p>Just publish invalidations with ids similar to 'Obj1', 'Obj2', ... 'Obj3'
 *
 */
public final class MainActivity extends Activity {

  /** Tag used in logging. */
  private static final String TAG = "TEA2:MainActivity";

  /** Ticl client configuration. */
  private static final int CLIENT_TYPE = 4; // Demo client ID.
  private static final byte[] CLIENT_NAME = "TEA2:eetrofoot".getBytes();

  /** Sender ID associated with 's Android Push Messaging quota. */
  private static final String SENDER_ID = "ipc.invalidation@gmail.com";

  /**
   * Keep track of current registration and object status. This should probably be implemented
   * using intents rather than static state but I don't want to distract from the 
   * essentials in this example.
   */
  public static final class State {
    private static final Map<ObjectId, String> lastInformedVersion =
        new HashMap<ObjectId, String>();
    private static volatile MainActivity currentActivity;

    public static void setVersion(ObjectId objectId, String version) {
      synchronized (lastInformedVersion) {
        lastInformedVersion.put(objectId, version);
      }
      refreshData();
    }
  }

  // Controls
  private TextView info;

  /** Called when the activity is first created. */
  @Override
  public void onCreate(Bundle savedInstanceState) {
    Log.i(TAG, "Creating main activity");
    super.onCreate(savedInstanceState);

    initializeGcm();

    // Create and start a notification client. When the client is available, or if there is an
    // existing client, AndroidListener.reissueRegistrations() is called.
    Context context = getApplicationContext();
    Intent startIntent = AndroidListener.createStartIntent(context, CLIENT_TYPE, CLIENT_NAME);
    context.startService(startIntent);

    // Setup UI.
    info = new TextView(this);
    setContentView(info);

    // Remember the current activity since the TICL service in this example communicates via
    // static state.
    State.currentActivity = this;
    refreshData();
  }

  /** Registers for Google Cloud Messaging (GCM) if there is no existing registration. */
  private void initializeGcm() {
    Context context = getApplicationContext();
    GCMRegistrar.checkDevice(context);
    GCMRegistrar.checkManifest(context);
    String regId = GCMRegistrar.getRegistrationId(context);
    if (regId.equals("")) {
      Log.i(TAG, "Not registered with GCM; registering");
      GCMRegistrar.register(context, SENDER_ID);
    } else {
      Log.i(TAG, "Already registered with GCM " + regId);
    }
  }

  /** Updates UI with current registration status and object versions. */
  private static void refreshData() {
    final MainActivity activity = State.currentActivity;
    if (null != activity) {
      final StringBuilder builder = new StringBuilder();
      builder.append("\nLast informed versions status\n---------------\n");
      synchronized (State.lastInformedVersion) {
        for (Entry<ObjectId, String> entry : State.lastInformedVersion.entrySet()) {
          builder.append(entry.getKey().toString()).append(" -> ").append(entry.getValue())
              .append("\n");
        }
      }
      activity.info.post(new Runnable() {
        @Override
        public void run() {
          activity.info.setText(builder.toString());
        }
      });
    }
  }
}
