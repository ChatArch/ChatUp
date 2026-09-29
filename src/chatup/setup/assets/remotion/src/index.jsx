import React from 'react';
import {AbsoluteFill, Composition, interpolate, registerRoot, spring, useCurrentFrame, useVideoConfig} from 'remotion';

const Welcome = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const entrance = spring({frame, fps, config: {damping: 18}});
  return (
    <AbsoluteFill style={{background: '#102a28', color: '#f1ebd9', overflow: 'hidden'}}>
      <div style={{position: 'absolute', width: 540, height: 540, borderRadius: '50%', background: '#d5ff63', right: -110, top: -160, transform: `scale(${entrance})`}} />
      <div style={{position: 'absolute', left: 80, top: 68, fontFamily: 'monospace', fontSize: 20, letterSpacing: 5}}>MOTION / 001</div>
      <div style={{position: 'absolute', left: 80, top: 200, opacity: entrance, transform: `translateY(${(1 - entrance) * 60}px)`}}>
        <div style={{fontFamily: 'Georgia, serif', fontSize: 112, lineHeight: 1.05}}>Ready to<br />make a move.</div>
        <div style={{marginTop: 35, fontFamily: 'monospace', fontSize: 22}}>REMOTION IS READY.</div>
      </div>
      <div style={{position: 'absolute', bottom: 0, height: 10, width: `${interpolate(frame, [0, 89], [0, 100])}%`, background: '#d5ff63'}} />
    </AbsoluteFill>
  );
};

const Root = () => <Composition id="Welcome" component={Welcome} durationInFrames={90} fps={30} width={1280} height={720} />;
registerRoot(Root);
