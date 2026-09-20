/* iNNOVULIS™ proprietary technology. Copyright © 2026 iNNOVULIS™.
 * Client-side animation reference: Unity compilation and rig binding are NOT verified.
 * Playback uses text-estimated cues; it does not synchronize to synthesized audio.
 */
using System;
using System.Collections;
using UnityEngine;

namespace SpotEm
{
    [Serializable]
    public class VisemeCue
    {
        public float time;
        public int visemeId;
        public float weight = 1f;
    }

    public class DigitalHumanVisemePlayer : MonoBehaviour
    {
        public SkinnedMeshRenderer face;
        // 0 = silence, 1..10 = authored rig's semantic mouth shapes.
        // Configure each index in Inspector for the selected mesh; -1 = unavailable.
        public int[] blendShapeIndexes = { -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 };
        Coroutine active;

        public void Play(VisemeCue[] cues)
        {
            if (active != null) StopCoroutine(active);
            ResetMouth();
            if (face != null && cues != null && cues.Length > 0)
                active = StartCoroutine(Animate(cues));
        }

        IEnumerator Animate(VisemeCue[] cues)
        {
            float elapsed = 0f;
            int next = 0;
            while (next < cues.Length)
            {
                elapsed += Time.deltaTime;
                while (next < cues.Length && elapsed >= cues[next].time)
                {
                    ResetMouth();
                    int shape = cues[next].visemeId;
                    if (shape >= 0 && shape < blendShapeIndexes.Length)
                    {
                        int index = blendShapeIndexes[shape];
                        if (index >= 0 && face.sharedMesh != null &&
                            index < face.sharedMesh.blendShapeCount)
                            face.SetBlendShapeWeight(index,
                                Mathf.Clamp01(cues[next].weight) * 100f);
                    }
                    next++;
                }
                yield return null;
            }
            yield return new WaitForSeconds(0.12f);
            ResetMouth();
            active = null;
        }

        void ResetMouth()
        {
            if (face == null || face.sharedMesh == null || blendShapeIndexes == null) return;
            foreach (int index in blendShapeIndexes)
                if (index >= 0 && index < face.sharedMesh.blendShapeCount)
                    face.SetBlendShapeWeight(index, 0f);
        }

        void OnDisable()
        {
            if (active != null) StopCoroutine(active);
            active = null;
            ResetMouth();
        }
    }
}
