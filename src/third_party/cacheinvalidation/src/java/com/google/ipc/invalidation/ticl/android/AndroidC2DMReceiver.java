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

package com.google.ipc.invalidation.ticl.android;

import com.google.ipc.invalidation.external.client.SystemResources.Logger;
import com.google.ipc.invalidation.external.client.android.service.AndroidLogger;
import com.google.ipc.invalidation.ticl.android.c2dm.BaseC2DMReceiver;

import android.content.Context;
import android.content.Intent;
import android.util.Base64;


/**
 * Service that handles system C2DM messages (with support from the {@link BaseC2DMReceiver} base
 * class. It receives intents for C2DM registration, errors and message delivery. It does some basic
 * processing and then forwards the messages to the {@link AndroidInvalidationService} for handling.
 *
 */
public class AndroidC2DMReceiver extends BaseC2DMReceiver {

  /** Logger */
  private static final String TAG = "InvC2DMReceiver";

  /** Logger */
  private static final Logger logger = AndroidLogger.forTag(TAG);

  public AndroidC2DMReceiver() {
    super(TAG, true);
  }

  @Override
  public void onRegistered(Context context, String registrationId) {
    logger.info("C2DM Registration received: %s", registrationId);

    // Upon receiving a new updated c2dm ID, notify the invalidation service
    Intent serviceIntent =
        AndroidInvalidationService.createRegistrationIntent(context, registrationId);
    context.startService(serviceIntent);
  }

  @Override
  public void onUnregistered(Context context) {
    logger.info("C2DM Registration revoked");

    // If the c2dm registration ID is revoked, also notify the invalidation service.
    Intent serviceIntent = AndroidInvalidationService.createRegistrationIntent(context, null);
    context.startService(serviceIntent);
  }

  @Override
  public void onRegistrationError(Context context, String errorId) {
    // Send any registration error to the invalidation service.
    Intent serviceIntent = AndroidInvalidationService.createErrorIntent(context, errorId);
    context.startService(serviceIntent);
  }

  @Override
  protected void onMessage(Context context, Intent intent) {
    // Extract expected fields and do basic syntactic checks (but no value checking)
    // and forward the result on to the AndroidInvalidationService for processing.
    Intent serviceIntent;
    String clientKey = intent.getStringExtra(AndroidC2DMConstants.CLIENT_KEY_PARAM);
    if (clientKey == null) {
      logger.severe("C2DM Intent does not contain client key value: %s", intent);
      return;
    }
    String encodedData = intent.getStringExtra(AndroidC2DMConstants.CONTENT_PARAM);
    String echoToken = intent.getStringExtra(AndroidC2DMConstants.ECHO_PARAM);
    if (encodedData != null) {
      try {
        byte [] rawData = Base64.decode(encodedData, Base64.URL_SAFE);
        serviceIntent = AndroidInvalidationService.createDataIntent(this, clientKey, echoToken,
            rawData);
      } catch (IllegalArgumentException exception) {
        logger.severe("Unable to decode intent data", exception);
        return;
      }
    } else {
      logger.severe("Received mailbox intent: %s", intent);
      return;
    }
    context.startService(serviceIntent);
  }
}
