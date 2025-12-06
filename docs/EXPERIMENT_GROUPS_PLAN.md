# Experiment Groups Feature Plan

## Goal
Allow users to:
1. Select multiple devices
2. Save them as named groups (e.g., "Experiment 1", "Experiment 2")
3. Create multiple groups that may overlap
4. Compare groups or view them separately

## Solution Options

### Option 1: Multiple Device Filter Variables (Recommended)
Create separate device filter variables for each experiment:
- `device_filter_exp1` - Experiment 1 devices
- `device_filter_exp2` - Experiment 2 devices
- `device_filter_exp3` - Experiment 3 devices
- etc.

**Pros:**
- Simple to implement
- Each experiment can be configured independently
- Can create panels showing each experiment separately
- Native Grafana functionality

**Cons:**
- Need to add new variables for each experiment
- Fixed number of experiments

### Option 2: Use Grafana Variable Sets
Create different variable sets that can be switched:
- Set 1: Experiment 1 configuration
- Set 2: Experiment 2 configuration
- etc.

**Pros:**
- Can switch between experiments easily
- One set of panels

**Cons:**
- More complex
- Can't view multiple experiments side-by-side easily

### Option 3: Custom Annotation/Labeling
Use Grafana annotations or custom fields to mark experiment periods and devices.

**Pros:**
- Flexible
- Can track experiment timeline

**Cons:**
- More complex
- Requires data model changes

## Recommended: Option 1

I'll implement Option 1 - multiple device filter variables for experiments.

### Implementation
1. Add 3 experiment device filter variables (can add more later)
2. Each has same device list but independent selection
3. Create panels that can filter by experiment
4. Or create separate panels for each experiment

### Usage
- Select devices for "Experiment 1" using `device_filter_exp1` dropdown
- Select devices for "Experiment 2" using `device_filter_exp2` dropdown
- View total power for each experiment
- Compare experiments side-by-side

Let me know if you want me to implement this!

