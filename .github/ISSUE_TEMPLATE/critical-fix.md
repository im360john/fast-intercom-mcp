---
name: Critical Fix
about: Template for critical issues that need implementation and quality control
title: '[CRITICAL] '
labels: ['critical', 'needs-implementation', 'qc-required']
assignees: ''
---

## Issue Type: CRITICAL-FIX

### Problem Description
<!-- Clear description of what's broken/incomplete -->

### Expected Outcome  
<!-- What should work after the fix -->

### Files to Modify
<!-- List specific files that need changes -->

### Quality Control Criteria
<!-- Specific, testable criteria for acceptance -->
- [ ] Test 1: 
- [ ] Test 2: 
- [ ] Test 3: 

### Implementation Notes
<!-- Technical details, code snippets, specific instructions -->

### Definition of Done
- [ ] Code implemented according to specifications
- [ ] Self-tested by implementer (all manual tests pass)
- [ ] Code follows existing patterns and conventions
- [ ] Ready for QC review

---

## Workflow Status

**Current Status:** `needs-implementation`

### Status Transitions:
1. **TODO** → `needs-implementation` label
2. **IN PROGRESS** → add `in-progress` label, assign to implementer
3. **READY FOR QC** → remove `in-progress`, add `ready-for-qc` label
4. **QC REVIEW** → QC agent tests all criteria:
   - **PASS** → add `qc-passed` label, close issue ✅
   - **FAIL** → add `qc-failed` label, comment with problems, reopen 🔄

### QC Instructions
When reviewing, test each checkbox in "Quality Control Criteria" and:
- ✅ If all criteria pass: Add `qc-passed` label and close issue
- ❌ If any fail: Add `qc-failed` label, comment with specific failures, reopen for rework