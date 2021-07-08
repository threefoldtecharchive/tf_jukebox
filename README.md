# blockchain_jukebox
provides an easy and simple way to deploy/manage block chain nodes on the TF Grid
## User should be able to 
  - Create nodes
  - List nodes
  - Delete nodes
  - Notified if those nodes about to expire / goes down
## Server should do the following
  - Respond to client requests (TG bot)
  - Do monitoring to the deployed nodes
  - Notify user when his nodes about to expire / goes down
# Structure
- Jukebox interface enables user to create, list and delete his nodes
- Server running jumpscale which the user will communicate to
- TF Grid: where the nodes lives, the server sends request to the grid to do the required action
