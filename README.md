# blockchain_jukebox
provides an easy and simple way to deploy/manage block chain nodes using a telegram bot
## User should be able to 
  - Create nodes
  - list nodes
  - Delete nodes
  - Notified if those nodes about to expire
## Server should do the following
  - Respond to client requests (TG bot)
  - Do monitoring to the deployed nodes
  - Notify user when his nodes about to expire
# Structure
- A telegram bot enables user to create, list and delete his nodes
- Server running jumpscale which the user will communicate to it through the telegram bot
- TF Grid: where the nodes lives, the server sends request to the grid to do the required action
