#include <iostream>
#include <string>
#include <gz/msgs.hh>
#include <gz/transport.hh>
 
bool srvEcho(const gz::msgs::StringMsg &_req,
  gz::msgs::StringMsg &_rep)
{
  // Set the response's content.
  _rep.set_data(_req.data());
 
  // The response succeed.
  return true;
}
 
int main(int argc, char **argv)
{
  // Let's print the list of our network interfaces.
  std::cout << "List of network interfaces in this machine:" << std::endl;
  for (const auto &netIface : gz::transport::determineInterfaces())
    std::cout << "\t" << netIface << std::endl;
 
  // Create a transport node.
  gz::transport::Node node;
  std::string service = "/echo";
 
  // Advertise a service call.
  if (!node.Advertise(service, srvEcho))
  {
    std::cerr << "Error advertising service [" << service << "]" << std::endl;
    return -1;
  }
 
  // Zzzzzz.
  gz::transport::waitForShutdown();
}
