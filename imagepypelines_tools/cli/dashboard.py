import subprocess
import sys

from ..app import socketio, app
from ..Chatroom import Chatroom
from .util import check_docker
from . import GENERAL_DASHBOARD_TAG, VERSION_DASHBOARD_TAG


DEFAULT_DASHBAORD_IP = "0.0.0.0"
DEFAULT_DASHBOARD_PORT = 5000
DEFAULT_CHATROOM_PORT = 9000

def dashboard(parser, args):
    """launches the dashboard"""
    # ideas for additonal flags (I just chose explicit names for now -JM)
    #
    # --timeout  --> timeout if no pipelines or clients connect to it
    # --from_file --> pulls config from a file
    # --restricted_access --> something for restricted access

    parser.add_argument("host",
                        help="IP address of the dashboard server to ping",
                        default=DEFAULT_DASHBAORD_IP,
                        type=str)
    parser.add_argument("port",
                        help="port number of the dashboard",
                        default=DEFAULT_DASHBAORD_PORT,
                        type=int)
    parser.add_argument('-c',
                        "--chatroom-port",
                        help="port number of the dashboard",
                        default=DEFAULT_CHATROOM_PORT,
                        type=int)
    parser.add_argument("--containerized",
                        help="whether or not to launch the dashboard in a docker container. Requires docker to be installed.",
                        action='store_true')
    parser.add_argument("--latest",
                        help="only applies if --containerized is used. whether or not to force the most recent image to be used",
                        action='store_true')

    args = parser.parse_args()

    print(f"launching dashboard at {args.host}:{args.port}...")
    if args.containerized:
        _docker_dashboard(parser,args)

    else:
        # this will be switched to execution using Gevent or WSGI (link from Jai)
        # https://flask.palletsprojects.com/en/1.1.x/deploying/wsgi-standalone/

        # start the chatroom
        chatroom = Chatroom(args.host,args.chatroom_port,socketio)
        chatroom.start()

        # launch the socketio app
        socketio.run(app, host=args.host, port=args.port)

        # stop the chatroom thread
        chatroom.stop_thread()


def _docker_dashboard(parser, args):
    """launches the dashboard"""
    # ideas for additonal flags (I just chose explicit names for now -JM)
    #
    # --timeout  --> timeout if no pipelines or clients connect to it
    # --from_file --> pulls config from a file
    # --restricted_access --> something for restricted access
    check_docker()


    tag = GENERAL_DASHBOARD_TAG
    # TODO: uncomment once version dashboard tags are supported
    # if args.latest:
    #     tag = GENERAL_DASHBOARD_TAG
    # else:
    #     tag = VERSION_DASHBOARD_TAG

    cmd = ['docker',
            'run',
            '--rm',
            '-p', f'{args.port}:{DEFAULT_DASHBAORD_PORT}',
            '-p', f'{args.chatroom_port}:{DEFAULT_CHATROOM_PORT}',
            tag]