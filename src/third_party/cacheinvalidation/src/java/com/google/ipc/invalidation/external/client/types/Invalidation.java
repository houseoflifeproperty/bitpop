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

package com.google.ipc.invalidation.external.client.types;

import com.google.common.base.Preconditions;

import java.util.Arrays;


/**
 * A class to represent an invalidation for a given object/version and an optional payload.
 *
 */
public final class Invalidation {

  /** The object being invalidated/updated. */
  private final ObjectId objectId;

  /** The new version of the object. */
  private final long version;

  /** Optional payload for the object. */
  private final byte[] payload;

  /** Creates an invalidation for the given {@code object} and {@code version}. */
  public static Invalidation newInstance(ObjectId objectId, long version) {
    return new Invalidation(objectId, version, null);
  }

  /**
   * Creates an invalidation for the given {@code object}, {@code version} and optional
   * {@code payload}.
   */
  public static Invalidation newInstance(ObjectId objectId, long version,
      byte[] payload) {
    return new Invalidation(objectId, version, payload);
  }

  /**
   * Creates an invalidation for the given {@code object}, {@code version} and optional
   * {@code payload} and optional {@code componentStampLog}.
   */
  private Invalidation(ObjectId objectId, long version, byte[] payload) {
    this.objectId = Preconditions.checkNotNull(objectId, "objectId");
    this.version = version;
    this.payload = payload;
  }

  public ObjectId getObjectId() {
    return objectId;
  }

  public long getVersion() {
    return version;
  }

  /** Returns the optional payload for the object - if none exists, returns {@code null}. */
  public byte[] getPayload() {
    return payload;
  }

  @Override
  public boolean equals(Object object) {
    if (object == this) {
      return true;
    }

    if (!(object instanceof Invalidation)) {
      return false;
    }

    final Invalidation other = (Invalidation) object;
    if ((payload != null) != (other.payload != null)) {
      // One of the objects has a payload and the other one does not.
      return false;
    }
    // Both have a payload or not.
    return objectId.equals(other.objectId) && (version == other.version) &&
    ((payload == null) || Arrays.equals(payload, other.payload));
  }

  @Override
  public int hashCode() {
    int result = 17;
    result = 31 * result + objectId.hashCode();
    result = 31 * result + (int) (version ^ (version >>> 32));
    if (payload != null) {
      result = 31 * result + Arrays.hashCode(payload);
    }
    return result;
  }

  @Override
  public String toString() {
    return "Inv: <" + objectId + ", " + version + ", " + BytesFormatter.toString(payload) + ">";
  }
}
