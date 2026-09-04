/**
 * File: local-workbench/components/ui/button.jsx
 * Purpose:
 *  - Provide the one focused button primitive used by the local 2.5D workbench.
 */

import { Button as ButtonPrimitive } from '@base-ui/react/button';

export function Button({ className = '', ...props }) {
  return <ButtonPrimitive className={className} {...props} />;
}
