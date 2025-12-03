# Admin UI - Device Group Manager

Simple web interface for managing device groups with checkboxes. Perfect for non-technical users to create experiment groups.

## Features

- ✅ **Checkbox Interface** - Simple checkboxes to select devices
- ✅ **Create Groups** - Name groups (e.g., "Experiment 1 - Streaming Test")
- ✅ **Edit Groups** - Update device selection for existing groups
- ✅ **Delete Groups** - Remove groups you no longer need
- ✅ **Auto-populated Device List** - Fetches devices from InfluxDB automatically

## Usage

1. **Access Admin UI**: http://localhost:7001
2. **Create Group**:
   - Enter group name
   - Check devices you want in this group
   - Click "Create Group"
3. **Edit Group**: Click "Edit" button, change device selection
4. **Delete Group**: Click "Delete" button

## How It Works

- Groups are stored in `/app/data/device_groups.json`
- Grafana dashboard can read these groups
- Each group is just a named list of device aliases

## API Endpoints

- `GET /` - Main UI page
- `GET /api/devices` - Get all available devices
- `GET /api/groups` - Get all device groups
- `POST /api/groups` - Create new group
- `PUT /api/groups/{name}` - Update existing group
- `DELETE /api/groups/{name}` - Delete group

## Example Group

```json
{
  "Experiment 1 - Streaming Test": {
    "name": "Experiment 1 - Streaming Test",
    "devices": ["London-Office-PC", "NYC-Studio-1", "LA-Encoder-2"],
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  }
}
```

