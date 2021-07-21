# Blockchain Jukebox
Provides an easy and simple way to deploy/manage blockchain nodes on the TF Grid.
## User should be able to 
  - Create nodes
  - List nodes
  - Delete nodes
  - Be notified if nodes are about to expire / goes down
## Server should do the following
  - Respond to client requests
  - Do monitoring of the deployed nodes
  - Notify user when nodes are about to expire / goes down
# Structure
- Jukebox interface enables user to create, list and delete blockchain nodes
- Server running jumpscale which users communicate to
- TF Grid: where the nodes live, the server sends request to the grid to do the required actions
