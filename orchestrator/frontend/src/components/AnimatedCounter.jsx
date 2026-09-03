import React, { useEffect, useRef } from 'react';
import { useSpring, useTransform, motion, useMotionValue } from 'framer-motion';

/**
 * AnimatedCounter — physics-based count-up number animation.
 * Used in dashboard summary stat cards.
 *
 * @param {number}   value      Target value to animate towards
 * @param {number}   duration   Animation duration in seconds (default 1.2)
 * @param {function} formatFn   Optional formatter (e.g. v => v.toLocaleString())
 * @param {string}   className  Optional CSS class for the wrapper span
 */
function AnimatedCounter({ value = 0, duration = 1.2, formatFn, className = '' }) {
  const motionVal = useMotionValue(0);
  const springVal = useSpring(motionVal, {
    duration: duration * 1000,
    bounce: 0,
  });
  const displayVal = useTransform(springVal, (v) => {
    const rounded = Math.round(v);
    return formatFn ? formatFn(rounded) : String(rounded);
  });

  const prevValueRef = useRef(0);

  useEffect(() => {
    // Only re-animate when value actually changes
    if (value !== prevValueRef.current) {
      motionVal.set(prevValueRef.current);
      motionVal.set(value);
      prevValueRef.current = value;
    }
  }, [value, motionVal]);

  return (
    <motion.span className={className}>
      {displayVal}
    </motion.span>
  );
}

export default AnimatedCounter;
